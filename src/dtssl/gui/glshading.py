"""Shader programs shared by the GL views (the 3D field tab and the Robot tab), ``pyqtgraph.opengl``.

pyqtgraph's stock ``shaded`` program lights the scene from behind the viewer's shoulder on the far side, which
leaves whatever faces the camera at 20 % of its colour: a black robot becomes a silhouette and any light part
that shows through it stands out as a white patch. :func:`headlight_shader` lights from above and to the right
of the viewer with 35 % ambient, both faces of a triangle alike, so the CAD colours read as in a CAD viewer.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

HEADLIGHT_SHADER = "dtssl_headlight"


def headlight_shader():
    """CAD-style lighting: a light above and to the right of the viewer, both faces lit, 35 % ambient. Built
    from the vertex shader of pyqtgraph's own ``shaded`` program (so it follows the pyqtgraph version) plus the
    fragment shader below; registered once under :data:`HEADLIGHT_SHADER` and returned as the ``ShaderProgram``
    (``GLMeshItem(shader=...)`` takes it). Returns ``"shaded"`` when anything is off, so drawing never depends
    on it."""
    try:
        from pyqtgraph.opengl import shaders as sh

        prog = sh.ShaderProgram.names.get(HEADLIGHT_SHADER)
        if prog is None:
            base = sh.ShaderProgram.names["shaded"]
            vert = [s for s in base.shaders if isinstance(s, sh.VertexShader)][0]
            frag = sh.FragmentShader("""
                #ifdef GL_ES
                precision mediump float;
                #endif
                varying vec4 v_color;
                varying vec3 v_normal;
                void main() {
                    float p = abs(dot(v_normal, normalize(vec3(0.35, 0.5, 0.8))));
                    vec3 rgb = v_color.rgb * (0.35 + 0.7 * p);
                    gl_FragColor = vec4(rgb, v_color.a);
                }
            """)
            prog = sh.ShaderProgram(HEADLIGHT_SHADER, [vert, frag])
        return prog
    except Exception as e:  # noqa: BLE001 - unexpected pyqtgraph internals: keep the stock shader
        log.warning("GL views: headlight shader unavailable (%s); using 'shaded'", e)
        return "shaded"


__all__ = ["HEADLIGHT_SHADER", "headlight_shader"]
