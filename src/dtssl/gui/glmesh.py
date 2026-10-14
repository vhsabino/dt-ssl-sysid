"""GL mesh items shared by the 3D views (``pyqtgraph.opengl``): :func:`mesh_item` builds the ``GLMeshItem`` of a
:class:`dtssl.gui.scene3d.Mesh` (smooth shading when the mesh carries normals, flat otherwise) and
:class:`InstancedMeshItem` draws one mesh at several transforms from a single item.

Why: ``pyqtgraph`` costs about 0.08 ms of Python per visible item per frame (GL state, matrices, attribute and
uniform lookups), whatever the mesh size; the 3D field view with 22 robots had 8 items per robot (183 in all,
22 ms per frame on an Intel Iris Xe) while the triangles themselves cost a few ms. Two items per robot (body +
the four wheels as instances) bring the frame back under 16 ms with more detailed wheels. Smooth normals are
computed here in numpy (``pyqtgraph``'s ``MeshData.vertexNormals`` loops over the vertices in Python).
"""
from __future__ import annotations

import logging

import numpy as np

from dtssl.gui import scene3d as S

log = logging.getLogger(__name__)

try:  # optional: PyOpenGL
    import pyqtgraph.opengl as gl
    from OpenGL import GL
    from PySide6 import QtGui

    GL_IMPORT_ERROR: str | None = None
except Exception as _e:  # noqa: BLE001 - ImportError or a GL loader failure
    gl = None
    GL = None
    GL_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"


if gl is not None:

    class FastMeshData(gl.MeshData):
        """``MeshData`` whose vertex normals come from :func:`scene3d.vertex_normals` (vectorised) or are
        given (``normals=``), instead of pyqtgraph's per-vertex Python loop."""

        def __init__(self, *args, normals=None, **kwargs):
            super().__init__(*args, **kwargs)
            if normals is not None:
                self._vertexNormals = np.asarray(normals, dtype=np.float32)

        def vertexNormals(self, indexed=None):  # noqa: N802 - pyqtgraph API
            if self._vertexNormals is None:
                self._vertexNormals = S.vertex_normals(self.vertexes(), self.faces()).astype(np.float32)
            return super().vertexNormals(indexed)

    class InstancedMeshItem(gl.GLMeshItem):
        """A ``GLMeshItem`` drawn once per transform of :meth:`set_instances` (the item's own transform is
        applied first). One Python ``paint`` for the four wheels of a robot: the VBOs are bound once and only
        the matrices change between the draw calls. Needs the VBO-based ``GLMeshItem`` of pyqtgraph >= 0.14
        (:func:`instancing_available`); with an older pyqtgraph use plain items."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._instances: list = []

        def set_instances(self, transforms) -> None:
            """``transforms``: ``QMatrix4x4`` list (world from the mesh frame of each instance)."""
            self._instances = list(transforms)
            self.update()

        def paint(self):
            if not self._instances:
                return
            self.setupGLState()
            if dirty_bits := self.parseMeshData():
                self.upload_vertex_buffers(dirty_bits)
            if not self.opts["drawFaces"] or self.vertexes is None:
                return
            view = self.view()
            proj = view.currentProjection()
            mv0 = view.currentModelView()
            context = QtGui.QOpenGLContext.currentContext()
            es2_compat = context.hasExtension(b"GL_ARB_ES2_compatibility")
            shader = self.shader()
            program = shader.program(es2_compat=es2_compat)
            enabled = []
            if (loc := GL.glGetAttribLocation(program, "a_position")) != -1:
                self.m_vbo_position.bind()
                GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, False, 0, None)
                self.m_vbo_position.release()
                enabled.append(loc)
            if (loc := GL.glGetAttribLocation(program, "a_normal")) != -1:
                if self.normals is None:
                    GL.glVertexAttrib3f(loc, 0, 0, 1)
                else:
                    self.m_vbo_normal.bind()
                    GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, False, 0, None)
                    self.m_vbo_normal.release()
                    enabled.append(loc)
            if (loc := GL.glGetAttribLocation(program, "a_color")) != -1:
                if self.colors is None:
                    color = self.opts["color"]
                    if isinstance(color, QtGui.QColor):
                        color = color.getRgbF()
                    GL.glVertexAttrib4f(loc, *color)
                else:
                    self.m_vbo_color.bind()
                    if self.colors.dtype == np.uint8:
                        GL.glVertexAttribPointer(loc, 4, GL.GL_UNSIGNED_BYTE, True, 0, None)
                    else:
                        GL.glVertexAttribPointer(loc, 4, GL.GL_FLOAT, False, 0, None)
                    self.m_vbo_color.release()
                    enabled.append(loc)
            for loc in enabled:
                GL.glEnableVertexAttribArray(loc)
            faces = self.faces
            with shader:
                loc_mvp = GL.glGetUniformLocation(program, "u_mvp")
                loc_normal = GL.glGetUniformLocation(program, "u_normal")
                if faces is not None:
                    self.m_ibo_faces.bind()
                for t in self._instances:
                    mv = mv0 * t
                    GL.glUniformMatrix4fv(loc_mvp, 1, False, np.array((proj * mv).data(), dtype=np.float32))
                    if loc_normal != -1:
                        GL.glUniformMatrix3fv(loc_normal, 1, False,
                                              np.array(mv.normalMatrix().data(), dtype=np.float32))
                    if faces is None:
                        GL.glDrawArrays(GL.GL_TRIANGLES, 0, int(np.prod(self.vertexes.shape[:-1])))
                    else:
                        GL.glDrawElements(GL.GL_TRIANGLES, faces.size, GL.GL_UNSIGNED_INT, None)
                if faces is not None:
                    self.m_ibo_faces.release()
            for loc in enabled:
                GL.glDisableVertexAttribArray(loc)

else:
    FastMeshData = None
    InstancedMeshItem = None


def instancing_available() -> bool:
    """True when the installed pyqtgraph has the VBO ``GLMeshItem`` that :class:`InstancedMeshItem` builds
    on (0.14 and later: ``upload_vertex_buffers`` and the ``currentModelView`` of the view)."""
    return (gl is not None and hasattr(gl.GLMeshItem, "upload_vertex_buffers")
            and hasattr(gl.GLMeshItem, "parseMeshData") and hasattr(gl.GLViewWidget, "currentModelView")
            and hasattr(gl.GLViewWidget, "currentProjection"))


def mesh_data(mesh: S.Mesh):
    """``MeshData`` of a mesh: per-vertex colours and the given normals when it is smooth (pyqtgraph draws a
    smooth, non face-indexed mesh with ``vertexColors``), per-face colours otherwise; a mesh without colours
    is drawn with the item's ``color``."""
    kw = {}
    if mesh.smooth:
        if mesh.vertex_colors is not None:
            kw["vertexColors"] = np.asarray(mesh.vertex_colors, dtype=np.float32)
        return FastMeshData(vertexes=mesh.vertices, faces=mesh.faces, normals=mesh.normals, **kw)
    if mesh.colors is not None:
        kw["faceColors"] = np.asarray(mesh.colors, dtype=np.float32)
    return FastMeshData(vertexes=mesh.vertices, faces=mesh.faces, **kw)


def mesh_item(mesh: S.Mesh, color, shader, cls=None, **opts):
    """``GLMeshItem`` (or ``cls``) of a mesh: smooth shading with the mesh normals when it has them, flat
    shading otherwise; ``color`` applies when the mesh has no colours of its own."""
    cls = cls or gl.GLMeshItem
    kw = dict(smooth=mesh.smooth, computeNormals=True, shader=shader, drawEdges=False, glOptions="opaque")
    kw.update(opts)
    if mesh.colors is None:
        kw["color"] = color
    return cls(meshdata=mesh_data(mesh), **kw)


__all__ = ["GL_IMPORT_ERROR", "FastMeshData", "InstancedMeshItem", "instancing_available", "mesh_data",
           "mesh_item"]
