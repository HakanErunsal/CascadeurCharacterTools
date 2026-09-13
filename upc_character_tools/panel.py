"""Qt Quick panel hosted by Cascadeur's existing QGuiApplication."""
from pathlib import Path
import traceback
import csc
from PySide6 import QtCore, QtQml
from . import core

_engine=None
_model=None

def default_export_dir():
    locations=[
        QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation),
        QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DownloadLocation),
        str(Path.home()),
    ]
    for location in locations:
        if not location:continue
        path=Path(location)/'CascadeurCharacterTools'/'Exports'
        try:
            path.mkdir(parents=True,exist_ok=True)
            return path
        except OSError:
            pass
    return Path.home()

def current_scene():
    view=csc.app.get_application().get_scene_manager().current_scene()
    if view is None:raise ValueError('Open a Cascadeur scene first.')
    return view.domain_scene()

class PanelModel(QtCore.QObject):
    changed=QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._selection='Select any control on one character.'
        self._status='Ready'
        self._busy=False
        self.export_dir=default_export_dir()
        self.timer=QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(700)

    @QtCore.Property(str,notify=changed)
    def selection(self):return self._selection
    @QtCore.Property(str,notify=changed)
    def status(self):return self._status
    @QtCore.Property(bool,notify=changed)
    def busy(self):return self._busy

    @QtCore.Slot()
    def refresh(self):
        if self._busy:return
        try:
            scene=current_scene();rig=core.resolve_character(scene);f=scene.get_layers_selector().selection().frames_interval()
            text=f"{rig['label']} · frames {f.first}–{f.last} · {f.last-f.first+1} frames"
        except Exception as e:text=str(e)
        if text!=self._selection:self._selection=text;self.changed.emit()

    def action(self,function):
        if self._busy:return
        self._busy=True;self._status='Working…';self.changed.emit()
        try:self._status=function()
        except Exception as e:
            self._status=str(e)
            try:current_scene().error('Manny tools: '+str(e))
            except Exception:pass
            print(traceback.format_exc())
        finally:self._busy=False;self.changed.emit();self.refresh()

    @QtCore.Slot(str,str,str,str,str)
    def addCharacter(self,name,x,y,z,yaw):
        def number(value,label):
            try: result=float(value.strip() or '0')
            except ValueError: raise ValueError(label+' must be a number.')
            if not core.math.isfinite(result):raise ValueError(label+' must be a finite number.')
            return result
        def operation():
            offset=[number(x,'X'),number(y,'Y'),number(z,'Z')]
            angle=number(yaw,'Yaw')
            return 'Added '+core.add_character(current_scene(),name,offset,angle)['label']+'. Undo removes this addition.'
        self.action(operation)

    @QtCore.Slot(int)
    def exportSelected(self,heading):
        try:
            scene=current_scene();rig=core.resolve_character(scene)
            frames=scene.get_layers_selector().selection().frames_interval();first,last=frames.first,frames.last
            stem=core.re.sub(r'[^A-Za-z0-9_-]+','_',rig['label'])
            suggestion=self.export_dir/f'{stem}_{first}_{last}.fbx'
            mode='body' if heading==0 else 'root'
            def save(path):
                if not path:return
                self.export_dir=Path(path).parent
                def operation():
                    result=core.export_character(scene,path,rig,first,last,mode)
                    return f"Exported {Path(path).name}\n{result['frames']} frames · {result['bone_count']} bones · starts at origin"
                self.action(operation)
            csc.app.get_application().get_file_dialog_manager().show_save_file_dialog('Export Manny animation',str(suggestion),['*.fbx'],save)
        except Exception as e:self._status=str(e);self.changed.emit()

def show_panel():
    global _engine,_model
    if _engine is None:
        _model=PanelModel()
        _engine=QtQml.QQmlApplicationEngine()
        _engine.rootContext().setContextProperty('toolModel',_model)
        _engine.load(QtCore.QUrl.fromLocalFile(str(Path(__file__).with_name('panel.qml'))))
        if not _engine.rootObjects():
            _engine=None
            raise RuntimeError('The Manny panel did not load. Check the Event Log.')
    window=_engine.rootObjects()[0]
    window.setProperty('visible', True)
    # A QML Window is exposed as QObject by Cascadeur's bundled PySide build.
    # Setting the property is portable; QWidget-only raise_() is not.
    QtCore.QMetaObject.invokeMethod(window, 'requestActivate')
    return window
