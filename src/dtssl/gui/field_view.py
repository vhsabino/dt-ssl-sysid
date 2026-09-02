"""Field view: SSL Div B field, robots, ball and trails in a ``QGraphicsView`` (1 scene unit = 1 mm).

The scene uses the ssl-vision frame directly (x to the right goal, **y up**); the view carries
a ``scale(1, -1)`` so +y is drawn upwards. Items are created once and moved on each
:meth:`FieldView.update_state` (no re-creation per frame).

Interaction: left click = teleport the selected robot there (signal ``robot_teleport_requested``),
right click = teleport the ball (``ball_teleport_requested``), Ctrl+left click on a robot =
select it (``robot_selected``); wheel = zoom under the cursor; left/middle drag = pan;
double click / ``F`` = fit the field.
"""
from __future__ import annotations

import math
from collections import deque

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QPointF, QRectF, Qt, Signal

from dtssl.sim.entities import WorldState
from dtssl.sim.world import FieldGeometry

MM = 1000.0
TEAM_COLORS = {"blue": QtGui.QColor(41, 121, 255), "yellow": QtGui.QColor(255, 214, 0)}
TRUTH_COLOR = QtGui.QColor(200, 200, 200, 160)
SIM_TRAIL_COLOR = QtGui.QColor(0, 229, 255)
TRUTH_TRAIL_COLOR = QtGui.QColor(255, 64, 129)
FIELD_GREEN = QtGui.QColor(34, 120, 52)
BOUNDARY_GREEN = QtGui.QColor(26, 92, 40)
LINE_WHITE = QtGui.QColor(245, 245, 245)
BALL_ORANGE = QtGui.QColor(255, 140, 0)


def _cosmetic_pen(color, width_px: float = 1.0, style=Qt.SolidLine) -> QtGui.QPen:
    pen = QtGui.QPen(QtGui.QColor(color), width_px, style)
    pen.setCosmetic(True)
    return pen


# =========================================================================== items
class RobotItem(QtWidgets.QGraphicsItem):
    """Disc with a flat front (dribbler face at ``front_mm``), heading line, id label."""

    def __init__(self, team: str, rid: int, radius_mm: float = 90.0, front_mm: float = 75.0,
                 color: QtGui.QColor | None = None, ghost: bool = False):
        super().__init__()
        self.team, self.rid = team, int(rid)
        self.radius, self.front = float(radius_mm), float(front_mm)
        self.color = color or TEAM_COLORS.get(team, QtGui.QColor(160, 160, 160))
        self.ghost = ghost
        self.selected_ = False
        self.has_ball = False
        self._path = self._build_path()
        self._label = QtWidgets.QGraphicsSimpleTextItem(str(self.rid), self)
        self._label.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self._label.setFont(font)
        self._label.setBrush(QtGui.QBrush(Qt.black if team == "yellow" else Qt.white))
        br = self._label.boundingRect()
        self._label.setTransform(QtGui.QTransform.fromTranslate(-br.width() / 2.0, -br.height() / 2.0))
        self.setZValue(5 if ghost else 10)
        if ghost:
            self.setOpacity(0.55)

    def _build_path(self) -> QtGui.QPainterPath:
        r, f = self.radius, self.front
        a = math.degrees(math.acos(max(-1.0, min(1.0, f / r))))      # half-angle of the flat chord
        path = QtGui.QPainterPath()
        rect = QRectF(-r, -r, 2 * r, 2 * r)
        # QPainterPath angles are CCW in a y-up frame; start at the chord's top end, sweep the long way
        path.arcMoveTo(rect, a)
        path.arcTo(rect, a, 360.0 - 2 * a)
        path.closeSubpath()
        return path

    def boundingRect(self) -> QRectF:
        m = self.radius + 12.0
        return QRectF(-m, -m, 2 * m, 2 * m)

    def shape(self) -> QtGui.QPainterPath:
        return self._path

    def paint(self, painter: QtGui.QPainter, option, widget=None) -> None:
        pen = _cosmetic_pen(Qt.white if self.selected_ else Qt.black, 3.0 if self.selected_ else 1.0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(self.color))
        painter.drawPath(self._path)
        if self.selected_:
            ring = _cosmetic_pen(QtGui.QColor(255, 255, 255, 200), 1.5, Qt.DashLine)
            painter.setPen(ring)
            painter.setBrush(Qt.NoBrush)
            m = self.radius + 8.0
            painter.drawEllipse(QRectF(-m, -m, 2 * m, 2 * m))
        painter.setPen(_cosmetic_pen(Qt.black, 2.0))
        painter.drawLine(QPointF(0.0, 0.0), QPointF(self.front, 0.0))
        if self.has_ball:
            painter.setPen(_cosmetic_pen(BALL_ORANGE, 3.0))
            painter.drawLine(QPointF(self.front, -30.0), QPointF(self.front, 30.0))

    # ------------------------------------------------------------------ updates
    def set_pose(self, x_m: float, y_m: float, theta: float) -> None:
        self.setPos(x_m * MM, y_m * MM)
        self.setRotation(math.degrees(theta))

    def set_selected(self, sel: bool) -> None:
        if sel != self.selected_:
            self.selected_ = bool(sel)
            self.update()

    def set_has_ball(self, has: bool) -> None:
        if has != self.has_ball:
            self.has_ball = bool(has)
            self.update()


class BallItem(QtWidgets.QGraphicsEllipseItem):
    """Ball (drawn larger than 21.5 mm for visibility); grows and fades when airborne."""

    def __init__(self, radius_mm: float = 21.5, draw_mm: float = 32.0):
        super().__init__(-draw_mm, -draw_mm, 2 * draw_mm, 2 * draw_mm)
        self.radius_mm, self.draw_mm = radius_mm, draw_mm
        self.setBrush(QtGui.QBrush(BALL_ORANGE))
        self.setPen(_cosmetic_pen(Qt.black, 1.0))
        self.setZValue(20)

    def set_state(self, x_m: float, y_m: float, z_m: float = 0.0) -> None:
        self.setPos(x_m * MM, y_m * MM)
        s = 1.0 + max(0.0, z_m) * 2.0
        self.setScale(s)
        self.setOpacity(1.0 if z_m <= 0.001 else max(0.4, 1.0 - z_m))


class TrailItem(QtWidgets.QGraphicsPathItem):
    """Polyline of the last ``seconds`` of a pose stream (rebuilt from a deque on each update)."""

    def __init__(self, color: QtGui.QColor, seconds: float = 3.0, width_px: float = 2.0, z: float = 3.0):
        super().__init__()
        self.seconds = float(seconds)
        self.points: deque[tuple[float, float, float]] = deque()
        self.setPen(_cosmetic_pen(color, width_px))
        self.setZValue(z)

    def clear(self) -> None:
        self.points.clear()
        self.setPath(QtGui.QPainterPath())

    def append(self, t: float, x_m: float, y_m: float) -> None:
        pts = self.points
        if pts and t < pts[-1][0]:          # time went backwards (reset / scrub): restart
            pts.clear()
        pts.append((t, x_m * MM, y_m * MM))
        horizon = t - self.seconds
        while pts and pts[0][0] < horizon:
            pts.popleft()

    def rebuild(self) -> None:
        path = QtGui.QPainterPath()
        it = iter(self.points)
        first = next(it, None)
        if first is None:
            self.setPath(path)
            return
        path.moveTo(first[1], first[2])
        for _, x, y in it:
            path.lineTo(x, y)
        self.setPath(path)


# =========================================================================== view
class FieldView(QtWidgets.QGraphicsView):
    robot_teleport_requested = Signal(float, float)     # x_m, y_m (left click)
    ball_teleport_requested = Signal(float, float)      # x_m, y_m (right click)
    robot_selected = Signal(str, int)                   # Ctrl+click on a robot

    def __init__(self, field: FieldGeometry | None = None, robot_radius_m: float = 0.09,
                 dribbler_offset_m: float = 0.075, ball_radius_m: float = 0.0215,
                 trail_seconds: float = 3.0, parent=None):
        super().__init__(parent)
        self.field = field or FieldGeometry()
        self.robot_radius_mm = robot_radius_m * MM
        self.front_mm = dribbler_offset_m * MM
        self.ball_radius_mm = ball_radius_m * MM
        self.trail_seconds = float(trail_seconds)
        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(20, 20, 20)))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.scale(1.0, -1.0)                                        # y up

        self.robots: dict[tuple[str, int], RobotItem] = {}
        self.ball = BallItem(self.ball_radius_mm)
        self.truth_robot: RobotItem | None = None
        self.sim_trail = TrailItem(SIM_TRAIL_COLOR, self.trail_seconds)
        self.truth_trail = TrailItem(TRUTH_TRAIL_COLOR, self.trail_seconds, z=2.5)
        self.selected: tuple[str, int] | None = None
        self.frames = 0
        self._user_zoom = False
        self._press_pos: QtCore.QPoint | None = None
        self._last_pos: QtCore.QPoint | None = None
        self._press_button = Qt.NoButton
        self._panned = False
        self._field_rect = QRectF()
        self._field_items: list[QtWidgets.QGraphicsItem] = []
        self._scene.addItem(self.sim_trail)
        self._scene.addItem(self.truth_trail)
        self._scene.addItem(self.ball)
        self.set_field(self.field)

    # ------------------------------------------------------------------ field drawing
    def set_field(self, field: FieldGeometry) -> None:
        self.field = field
        for it in self._field_items:
            self._scene.removeItem(it)
        self._field_items = []
        self._draw_field()
        self.fit_field()

    def _draw_field(self) -> None:
        f = self.field
        L, W = f.length * MM, f.width * MM
        bw = f.boundary_width * MM
        gw, gd = f.goal_width * MM, f.goal_depth * MM
        pd, pw = f.penalty_area_depth * MM, f.penalty_area_width * MM
        lt = max(1.0, f.line_thickness * MM)
        items: list[QtWidgets.QGraphicsItem] = []
        outer = QRectF(-L / 2 - bw, -W / 2 - bw, L + 2 * bw, W + 2 * bw)
        bg = self._scene.addRect(outer, QtGui.QPen(Qt.NoPen), QtGui.QBrush(BOUNDARY_GREEN))
        bg.setZValue(-10)
        items.append(bg)
        fld = self._scene.addRect(QRectF(-L / 2, -W / 2, L, W), QtGui.QPen(Qt.NoPen), QtGui.QBrush(FIELD_GREEN))
        fld.setZValue(-9)
        items.append(fld)
        pen = QtGui.QPen(LINE_WHITE, lt)
        pen.setCapStyle(Qt.FlatCap)
        for rect in (QRectF(-L / 2, -W / 2, L, W),                         # touch + goal lines
                     QRectF(-L / 2, -pw / 2, pd, pw),                        # left penalty area
                     QRectF(L / 2 - pd, -pw / 2, pd, pw)):                   # right penalty area
            it = self._scene.addRect(rect, pen)
            it.setZValue(-5)
            items.append(it)
        mid = self._scene.addLine(0.0, -W / 2, 0.0, W / 2, pen)
        mid.setZValue(-5)
        items.append(mid)
        r = f.center_circle_radius * MM
        cc = self._scene.addEllipse(QRectF(-r, -r, 2 * r, 2 * r), pen)
        cc.setZValue(-5)
        items.append(cc)
        dot = self._scene.addEllipse(QRectF(-lt * 2, -lt * 2, lt * 4, lt * 4), QtGui.QPen(Qt.NoPen),
                                     QtGui.QBrush(LINE_WHITE))
        dot.setZValue(-5)
        items.append(dot)
        gpen = QtGui.QPen(QtGui.QColor(230, 230, 230), lt * 2)
        for sx in (-1.0, 1.0):
            x0 = sx * L / 2
            x1 = sx * (L / 2 + gd)
            goal = QtGui.QPainterPath(QPointF(x0, -gw / 2))
            goal.lineTo(x1, -gw / 2)
            goal.lineTo(x1, gw / 2)
            goal.lineTo(x0, gw / 2)
            g = self._scene.addPath(goal, gpen)
            g.setZValue(-5)
            items.append(g)
            d = f.goal_center_to_penalty_mark * MM
            if 0.0 < d < L / 2:                                             # penalty mark (if inside the field)
                pm = self._scene.addEllipse(QRectF(sx * (L / 2 - d) - lt, -lt, 2 * lt, 2 * lt),
                                            QtGui.QPen(Qt.NoPen), QtGui.QBrush(LINE_WHITE))
                pm.setZValue(-5)
                items.append(pm)
        self._field_items = items
        self._field_rect = outer
        margin = 2.0 * MM
        self._scene.setSceneRect(outer.adjusted(-margin, -margin, margin, margin))

    def fit_field(self) -> None:
        if self._field_rect.isNull():
            return
        self.fitInView(self._field_rect.adjusted(-100, -100, 100, 100), Qt.KeepAspectRatio)
        self._user_zoom = False

    # ------------------------------------------------------------------ coordinates
    @staticmethod
    def scene_from_m(x_m: float, y_m: float) -> QPointF:
        return QPointF(x_m * MM, y_m * MM)

    @staticmethod
    def m_from_scene(pt: QPointF) -> tuple[float, float]:
        return (pt.x() / MM, pt.y() / MM)

    @staticmethod
    def scene_from_mm(x_mm: float, y_mm: float) -> QPointF:
        return QPointF(float(x_mm), float(y_mm))

    @staticmethod
    def mm_from_scene(pt: QPointF) -> tuple[float, float]:
        return (pt.x(), pt.y())

    def px_from_m(self, x_m: float, y_m: float) -> QPointF:
        """World (m) -> viewport pixel (float; includes zoom, pan and the y flip)."""
        return self.viewportTransform().map(self.scene_from_m(x_m, y_m))

    def m_from_px(self, px: QPointF) -> tuple[float, float]:
        inv, _ok = self.viewportTransform().inverted()
        return self.m_from_scene(inv.map(QPointF(px)))

    def px_per_mm(self) -> float:
        return abs(self.transform().m11())

    # ------------------------------------------------------------------ state updates
    def robot_item(self, team: str, rid: int) -> RobotItem:
        key = (team, int(rid))
        it = self.robots.get(key)
        if it is None:
            it = RobotItem(team, rid, self.robot_radius_mm, self.front_mm)
            it.set_selected(key == self.selected)
            self._scene.addItem(it)
            self.robots[key] = it
        return it

    def set_selected(self, key: tuple[str, int] | None) -> None:
        if key == self.selected:
            return
        if self.selected in self.robots:
            self.robots[self.selected].set_selected(False)
        self.selected = key
        if key in self.robots:
            self.robots[key].set_selected(True)
        self.sim_trail.clear()
        self.truth_trail.clear()

    def set_trail_seconds(self, seconds: float) -> None:
        self.trail_seconds = float(seconds)
        self.sim_trail.seconds = self.trail_seconds
        self.truth_trail.seconds = self.trail_seconds

    def clear_trails(self) -> None:
        self.sim_trail.clear()
        self.truth_trail.clear()

    def set_ball_visible(self, visible: bool) -> None:
        self.ball.setVisible(bool(visible))

    def update_state(self, ws: WorldState, selected: tuple[str, int] | None = None,
                     truth_pose: tuple[float, float, float] | None = None, t: float | None = None) -> None:
        """Move every item to ``ws`` (robots absent from ``ws`` or not present are hidden)."""
        seen = set()
        for key, r in ws.robots.items():
            it = self.robot_item(*key)
            seen.add(key)
            if not r.present:
                it.setVisible(False)
                continue
            it.setVisible(True)
            it.set_pose(r.x, r.y, r.theta)
            it.set_has_ball(r.has_ball)
        for key, it in self.robots.items():
            if key not in seen:
                it.setVisible(False)
        if selected != self.selected:
            self.set_selected(selected)
        b = ws.ball
        self.ball.set_state(b.x, b.y, b.z)
        tt = ws.t if t is None else t
        sel = self.selected
        if sel is not None and sel in ws.robots and ws.robots[sel].present:
            r = ws.robots[sel]
            self.sim_trail.append(tt, r.x, r.y)
            self.sim_trail.rebuild()
        if truth_pose is not None:
            if self.truth_robot is None:
                team = sel[0] if sel is not None else "blue"
                self.truth_robot = RobotItem(team, sel[1] if sel is not None else 0, self.robot_radius_mm,
                                             self.front_mm, color=TRUTH_COLOR, ghost=True)
                self._scene.addItem(self.truth_robot)
            self.truth_robot.setVisible(True)
            self.truth_robot.set_pose(*truth_pose)
            self.truth_trail.append(tt, truth_pose[0], truth_pose[1])
            self.truth_trail.rebuild()
        elif self.truth_robot is not None:
            self.truth_robot.setVisible(False)
        self.frames += 1

    def robot_at(self, scene_pt: QPointF) -> tuple[str, int] | None:
        for key, it in self.robots.items():
            if it.isVisible() and (it.pos() - scene_pt).manhattanLength() <= 1.5 * self.robot_radius_mm:
                return key
        return None

    # ------------------------------------------------------------------ interaction
    def wheelEvent(self, ev: QtGui.QWheelEvent) -> None:
        delta = ev.angleDelta().y()
        if delta == 0:
            return
        f = 1.15 ** (delta / 120.0)
        self.scale(f, f)
        self._user_zoom = True
        ev.accept()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self._press_pos = ev.position().toPoint()
        self._last_pos = self._press_pos
        self._press_button = ev.button()
        self._panned = False
        if ev.button() == Qt.MiddleButton:
            self.setCursor(Qt.ClosedHandCursor)
        ev.accept()

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        pos = ev.position().toPoint()
        if self._press_pos is not None and self._press_button in (Qt.LeftButton, Qt.MiddleButton):
            if self._panned or (pos - self._press_pos).manhattanLength() > 6:
                self._panned = True
                self.setCursor(Qt.ClosedHandCursor)
                d = pos - (self._last_pos or pos)
                hs, vs = self.horizontalScrollBar(), self.verticalScrollBar()
                hs.setValue(hs.value() - d.x())
                vs.setValue(vs.value() - d.y())
        self._last_pos = pos
        ev.accept()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.setCursor(Qt.ArrowCursor)
        if self._press_pos is not None and not self._panned:
            pt = self.mapToScene(ev.position().toPoint())
            x, y = self.m_from_scene(pt)
            if ev.button() == Qt.LeftButton:
                if ev.modifiers() & Qt.ControlModifier:
                    key = self.robot_at(pt)
                    if key is not None:
                        self.robot_selected.emit(key[0], key[1])
                else:
                    self.robot_teleport_requested.emit(x, y)
            elif ev.button() == Qt.RightButton:
                self.ball_teleport_requested.emit(x, y)
        self._press_pos = None
        self._press_button = Qt.NoButton
        self._panned = False
        ev.accept()

    def mouseDoubleClickEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.fit_field()
        ev.accept()

    def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:
        if ev.key() == Qt.Key_F:
            self.fit_field()
            ev.accept()
            return
        ev.ignore()                      # let the window's event filter drive the keyboard fallback

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        super().resizeEvent(ev)
        if not self._user_zoom:
            self.fit_field()


__all__ = ["FieldView", "RobotItem", "BallItem", "TrailItem", "MM", "TEAM_COLORS"]
