from __future__ import division
import FreeCADGui as Gui
from PySide import QtGui, QtCore

import numpy
import numpy as np
from copy import deepcopy

from openglider.glider.in_out.export_3d import ppm_Panels
from openglider.utils.distribution import Distribution
from ._tools import BaseTool, input_field, text_field
from .pivy_primitives_new_new import Container, Marker, coin, Line, COLORS


import matplotlib
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

def refresh():
    pass

class MplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = plt.figure(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        self.axes = self.fig.add_subplot(111)
        self.setParent(parent)
        self.updateGeometry()

    def plot(self, *args, **kwargs):
        self.axes.plot(*args, **kwargs)


class polars():
    try:
        ppm = __import__("ppm")
        pan3d = __import__("ppm.pan3d", globals(), locals(), ["abc"])
        ppm_utils = __import__("ppm.utils", globals(), locals(), ["abc"])
    except ImportError:
        ppm = None

    def __init__(self, obj):
        self.obj = obj
        self.ParametricGlider = deepcopy(self.obj.ParametricGlider)
        self.create_potential_table()
        self.solve_const_vert_Force()

    
    def create_potential_table(self):
        if not self.ppm:
            self.QWarning = QtGui.QLabel("no panel_method installed")
            self.layout.addWidget(self.QWarning)
        else:
            self._vertices, self._panels, self._trailing_edges = ppm_Panels(
                self.ParametricGlider.get_glider_3d(),
                midribs=0,
                profile_numpoints=50,
                num_average=4,
                distribution=Distribution.nose_cos_distribution(0.2),
                symmetric=True
                )
            case = self.pan3d.DirichletDoublet0Source0Case3(self._panels, self._trailing_edges)
            case.A_ref = self.ParametricGlider.shape.area
            case.mom_ref_point = self.ppm.Vector3(1.25, 0, -6)
            case.v_inf = self.ppm.Vector(self.ParametricGlider.v_inf)
            case.drag_calc = "trefftz"
            case.farfield = 5
            case.create_wake(10000000, 20)
            pols = case.polars(self.ppm_utils.vinf_deg_range3(case.v_inf, 5, 15, 20))
            self.cL = []
            self.cDi = []
            self.cPi = []
            self.alpha = []
            for i in pols.values:
                self.alpha.append(i.alpha)
                self.cL.append(i.cL)
                self.cDi.append(i.cD)
                self.cPi.append(i.cP)

    def potentialPlot(self):
        self.canvas = MplCanvas()
        self.canvas.plot(cD, cL, label="Drag $c_D * 10$")
        self.canvas.plot(cP, cL, label="Pitch -$c_P$")
        self.canvas.axes.xaxis.set_label("$\\alpha$")
        self.canvas.axes.legend()
        self.canvas.axes.grid()
        self.canvas.draw()
        self.canvas.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.canvas.show()

    def solve_const_vert_Force(self):
        from scipy.optimize import newton_krylov
        from scipy import interpolate
        # constants:
        c0 = 0.01        # const profile drag
        c2 = 0.01        # c2 * alpha**2 + c0 = cDpr
        cDpi = 0.01     # drag cooefficient of pilot
        cDl = 0.02      # line drag
        rho = 1.2
        mass = 90
        g = 9.81
        area = self.ParametricGlider.shape.area

        def minimize(velocity):
            alpha = np.array(self.alpha)
            cL = np.array(self.cL)
            cDi = np.array(self.cDi)
            force_factor = rho * velocity ** 2 / 2 * area
            gravity_force = np.ones_like(alpha) * (- mass * g)
            lift_vert_force = cL * force_factor * np.cos(alpha)
            drag_vert_force = (cDi + np.ones_like(alpha) * (cDpi + cDl + c0) + c2 * alpha**2) * force_factor
            return gravity_force + lift_vert_force + drag_vert_force

        def force_gz():
            alpha = np.array(self.alpha)
            cDi = np.array(self.cDi)
            cL_ges = np.array(self.cL)
            cD_ges = cDi + np.ones_like(alpha) * (cDpi + cDl + c0) + c2 * alpha**2
            return cL_ges / cD_ges
        sol = newton_krylov(minimize, np.ones_like(self.alpha))
        canvas = MplCanvas()
        canvas.plot(sol, 1 / np.tan(self.alpha), label="solution for const vert_lift")
        canvas.plot(sol, force_gz(), label="cA/cD")
        canvas.axes.legend()
        canvas.axes.grid()
        canvas.draw()
        canvas.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        canvas.show()

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()


class PanelTool(BaseTool):
    try:
        ppm = __import__("ppm")
        pan3d = __import__("ppm.pan3d", globals(), locals(), ["abc"])
    except ImportError:
        ppm = None

    def __init__(self, obj):
        super(PanelTool, self).__init__(obj, widget_name="Properties", hide=True)
        if not self.ppm:
            self.QWarning = QtGui.QLabel("no panel_method installed")
            self.layout.addWidget(self.QWarning)
        else:
            self.case = None
            self.Qrun = QtGui.QPushButton("run")
            self.Qmidribs = QtGui.QSpinBox()
            self.Qsymmetric = QtGui.QCheckBox()
            self.Qmean_profile = QtGui.QCheckBox()
            self.Qprofile_points = QtGui.QSpinBox()
            self.Qstream_points = QtGui.QSpinBox()
            self.Qstream_radius = QtGui.QDoubleSpinBox()
            self.Qstream_interval = QtGui.QDoubleSpinBox()
            self.Qstream_num = QtGui.QSpinBox()
            self.Qmax_val = QtGui.QDoubleSpinBox()
            self.Qmin_val = QtGui.QDoubleSpinBox()
            self.cpc = Container()
            self.stream = coin.SoSeparator()
            self.glider_result = coin.SoSeparator()
            self.marker = Marker([[0, 0, 0]], dynamic=True)
            self.setup_widget()
            self.setup_pivy()

    def setup_widget(self):
        self.layout.setWidget(0, text_field, QtGui.QLabel("profile points"))
        self.layout.setWidget(0, input_field, self.Qprofile_points)
        self.layout.setWidget(1, text_field, QtGui.QLabel("midribs"))
        self.layout.setWidget(1, input_field, self.Qmidribs)
        self.layout.setWidget(2, text_field, QtGui.QLabel("symmetric"))
        self.layout.setWidget(2, input_field, self.Qsymmetric)
        self.layout.setWidget(3, text_field, QtGui.QLabel("mean profile"))
        self.layout.setWidget(3, input_field, self.Qmean_profile)
        self.layout.setWidget(4, text_field, QtGui.QLabel("number of streams"))
        self.layout.setWidget(4, input_field, self.Qstream_points)
        self.layout.setWidget(5, text_field, QtGui.QLabel("stream radius"))
        self.layout.setWidget(5, input_field, self.Qstream_radius)
        self.layout.setWidget(6, text_field, QtGui.QLabel("points per streamline"))
        self.layout.setWidget(6, input_field, self.Qstream_num)
        self.layout.setWidget(7, text_field, QtGui.QLabel("stream interval"))
        self.layout.setWidget(7, input_field, self.Qstream_interval)
        self.layout.setWidget(8, text_field, QtGui.QLabel("min_val"))
        self.layout.setWidget(8, input_field, self.Qmin_val)
        self.layout.setWidget(9, text_field, QtGui.QLabel("max_val"))
        self.layout.setWidget(9, input_field, self.Qmax_val)
        self.layout.addWidget(self.Qrun)

        self.Qmidribs.setMaximum(5)
        self.Qmidribs.setMinimum(0)
        self.Qmidribs.setValue(0)
        self.Qprofile_points.setMaximum(50)
        self.Qprofile_points.setMinimum(10)
        self.Qprofile_points.setValue(20)
        self.Qsymmetric.setChecked(True)
        self.Qmean_profile.setChecked(True)
        self.Qstream_points.setMaximum(30)
        self.Qstream_points.setMinimum(1)
        self.Qstream_points.setValue(3)
        self.Qstream_radius.setMaximum(2)
        self.Qstream_radius.setMinimum(0)
        self.Qstream_radius.setValue(0.1)
        self.Qstream_radius.setSingleStep(0.1)
        self.Qstream_interval.setMaximum(1.000)
        self.Qstream_interval.setMinimum(0.00001)
        self.Qstream_interval.setValue(0.02)
        self.Qstream_interval.setSingleStep(0.01)

        self.Qstream_num.setMaximum(300)
        self.Qstream_num.setMinimum(5)
        self.Qstream_num.setValue(70)

        self.Qmin_val.setMaximum(3)
        self.Qmin_val.setMinimum(-10)
        self.Qmin_val.setValue(-3)
        self.Qmin_val.setSingleStep(0.001)

        self.Qmax_val.setMaximum(10)
        self.Qmax_val.setMinimum(0)
        self.Qmax_val.setValue(1)
        self.Qmax_val.setSingleStep(0.01)


        self.Qstream_points.valueChanged.connect(self.update_stream)
        self.Qstream_radius.valueChanged.connect(self.update_stream)
        self.Qstream_interval.valueChanged.connect(self.update_stream)
        self.Qstream_num.valueChanged.connect(self.update_stream)

        self.Qmin_val.valueChanged.connect(self.show_glider)
        self.Qmax_val.valueChanged.connect(self.show_glider)

        self.Qrun.clicked.connect(self.run)

    def setup_pivy(self):
        self.cpc.register(self.view)
        self.task_separator.addChild(self.cpc)
        self.task_separator.addChild(self.stream)
        self.task_separator.addChild(self.glider_result)
        self.cpc.addChild(self.marker)
        self.marker.on_drag_release.append(self.update_stream)
        self.marker.on_drag.append(self.update_stream_fast)

    def update_stream(self):
        self.stream.removeAllChildren()
        if self.case:
            point = list(self.marker.points[0].getValue())
            points = numpy.random.random((self.Qstream_points.value(), 3)) - numpy.array([0.5, 0.5, 0.5])
            points *= self.Qstream_radius.value()
            points += numpy.array(point)
            points = points.tolist()
            for p in points:
                pts = self.stream_line(p, self.Qstream_interval.value(), self.Qstream_num.value())
                self.stream.addChild(Line(pts, dynamic=False))

    def update_stream_fast(self):
        self.stream.removeAllChildren()
        if self.case:
            point = list(self.marker.points[0].getValue())
            pts = self.stream_line(point, 0.05, 10)
            self.stream.addChild(Line(pts, dynamic=False))

    def update_glider(self):
        self.obj.ViewObject.num_ribs = self.Qmidribs.value()
        self.obj.ViewObject.profile_num = self.Qprofile_points.value()

    def stream_line(self, point, interval, numpoints):
        flow_path = self.case.flow_path(self.ppm.Vector3(*point), interval, numpoints)
        return [[p.x, p.y, p.z] for p in flow_path]

    def create_panels(self, midribs=0, profile_numpoints=10, mean=False, symmetric=True):
        self._vertices, self._panels, self._trailing_edges = ppm_Panels(
            self.ParametricGlider.get_glider_3d(),
            midribs=midribs,
            profile_numpoints=profile_numpoints,
            num_average=mean*5,
            distribution=Distribution.nose_cos_distribution(0.2),
            symmetric=symmetric)

    def run(self):
        self.update_glider()
        self.create_panels(self.Qmidribs.value(), self.Qprofile_points.value(),
                           self.Qmean_profile.isChecked(), self.Qsymmetric.isChecked())
        self.case = self.pan3d.DirichletDoublet0Source0Case3(self._panels, self._trailing_edges)
        self.case.v_inf = self.ppm.Vector(self.ParametricGlider.v_inf)
        self.case.farfield = 5
        self.case.create_wake(9999, 10)
        self.case.run()
        self.show_glider()

    def show_glider(self):
        self.glider_result.removeAllChildren()
        verts = [list(i) for i in self.case.vertices]
        cols = [i.cp for i in self.case.vertices]
        pols = []
        pols_i =[]
        count = 0
        count_krit = (self.Qmidribs.value() + 1) * (self.Qprofile_points.value() - self.Qprofile_points.value() % 2)
        for pan in self._panels[::-1]:
            count += 1
            for vert in pan.points:
                #verts.append(list(vert))
                pols_i.append(vert.nr)
            pols_i.append(-1)     # end of pol
            if count % count_krit == 0:
                pols.append(pols_i)
                pols_i = []
        if pols_i:
            pols.append(pols_i)
        vertex_property = coin.SoVertexProperty()

        for i, col in enumerate(cols):
            vertex_property.orderedRGBA.set1Value(i, coin.SbColor(self.color(col)).getPackedValue())
            
        vertex_property.vertex.setValues(0, len(verts), verts)
        vertex_property.materialBinding = coin.SoMaterialBinding.PER_VERTEX_INDEXED

        vertex_property.normalBinding = coin.SoNormalBinding.PER_FACE

        shape_hint = coin.SoShapeHints()
        shape_hint.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
        shape_hint.creaseAngle = numpy.pi / 2
        self.glider_result.addChild(shape_hint)
        self.glider_result.addChild(vertex_property)
        for panels in pols:
            face_set = coin.SoIndexedFaceSet()
            face_set.coordIndex.setValues(0, len(panels), panels)
            self.glider_result.addChild(face_set)


        p1 = numpy.array(self.case.center_of_pressure)
        f = numpy.array(self.case.force)
        line = Line([p1, p1 + f])
        self.glider_result.addChild(line)

    def color(self, value):
        def f(n, i, x):
            if ((i - 1) / n) < x < (i / n):
                return (n * x + 1 - i)
            elif (i / n) <= x < ((i + 1) / n):
                return  (- n * x + 1 + i)
            else:
                return 0
        max_val=self.Qmax_val.value()
        min_val=self.Qmin_val.value()
        red = numpy.array(COLORS["red"])
        blue = numpy.array(COLORS["blue"])
        yellow = numpy.array(COLORS["yellow"])
        white = numpy.array(COLORS["white"])
        norm_val = (value - min_val) / (max_val - min_val)
        return list(f(3, 0, norm_val) * red + f(3,1,norm_val) * yellow + f(3,2,norm_val) * white + f(3,3,norm_val) * blue)


def create_fem_dict(par_glider):
    # create a ppm object and compute the pressure

    # create a dict with:
    #   nodes, elements, forces, bc, joints
    vertices, panels, trailing_edges = ppm_Panels(
        par_glider.get_glider_3d(),
        midribs=0,
        profile_numpoints=50,
        num_average=4,
        distribution=Distribution.nose_cos_distribution(0.2),
        symmetric=True
        )
    case.A_ref = par_glider.flat_area
    case.v_inf = ppm.Vector(glider.v_inf)
    self.case.farfield = 5
    self.case.create_wake(9999, 10)
    self.case.run()
