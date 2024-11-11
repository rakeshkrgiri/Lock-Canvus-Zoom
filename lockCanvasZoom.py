import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QObject, QEvent, Qt
from qgis.core import QgsRectangle
from qgis.gui import QgsMapToolPan

class ZoomLockFilter(QObject):
    def __init__(self, lock_canvas_zoom):
        super().__init__()
        self.lock_canvas_zoom = lock_canvas_zoom

    def eventFilter(self, obj, event):
        # Intercept wheel events to pan instead of zoom
        if event.type() == QEvent.Wheel and self.lock_canvas_zoom.zoom_locked:
            self.lock_canvas_zoom.activate_pan_tool(event)  # Use pan tool on scroll
            event.accept()
            return True
        return super().eventFilter(obj, event)

class LockCanvasZoom:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.zoom_locked = False
        self.action = None
        self.plugin_dir = os.path.dirname(__file__)
        self.locked_zoom_scale = None
        self.event_filter = ZoomLockFilter(self)
        self.pan_tool = QgsMapToolPan(self.canvas)  # Initialize QGIS Pan tool

    def initGui(self):
        # Set up toolbar icon for locking/unlocking zoom
        lock_icon_path = os.path.join(self.plugin_dir, "images", "lock.png")
        self.action = QAction(QIcon(lock_icon_path), "Lock Canvas Zoom", self.iface.mainWindow())
        self.action.triggered.connect(self.toggle_zoom_lock)
        self.iface.addToolBarIcon(self.action)
        
        # Install event filter on the canvas
        self.canvas.installEventFilter(self.event_filter)

    def activate_pan_tool(self, event):
        # Temporarily switch to the pan tool to handle the wheel event for panning
        original_tool = self.canvas.mapTool()  # Save the current map tool
        self.canvas.setMapTool(self.pan_tool)  # Set pan tool temporarily
        self.pan_tool.canvasMoveEvent(event)  # Trigger pan action with wheel event
        self.canvas.setMapTool(original_tool)  # Restore the original tool

    def toggle_zoom_lock(self):
        unlock_icon_path = os.path.join(self.plugin_dir, "images", "unlock.png")
        lock_icon_path = os.path.join(self.plugin_dir, "images", "lock.png")

        try:
            if not self.zoom_locked:
                # Lock the current zoom level (without locking extent)
                self.locked_zoom_scale = self.canvas.scale()  # Store the current scale only
                self.canvas.scaleChanged.connect(self.lock_zoom_scale)
                self.action.setIcon(QIcon(unlock_icon_path))
                self.action.setText("Unlock Canvas Zoom")
                self.zoom_locked = True
            else:
                # Unlock the zoom level
                self.canvas.scaleChanged.disconnect(self.lock_zoom_scale)
                self.action.setIcon(QIcon(lock_icon_path))
                self.action.setText("Lock Canvas Zoom")
                self.zoom_locked = False
                self.locked_zoom_scale = None
        except Exception as e:
            print("Error toggling zoom lock:", e)

    def lock_zoom_scale(self):
        # Reset the canvas scale if it changes (keep scale fixed)
        if self.locked_zoom_scale and self.canvas.scale() != self.locked_zoom_scale:
            self.canvas.zoomScale(self.locked_zoom_scale)  # Reset to locked scale

    def unload(self):
        # Remove toolbar icon and event filter when plugin is unloaded
        self.iface.removeToolBarIcon(self.action)
        if self.zoom_locked:
            try:
                self.canvas.scaleChanged.disconnect(self.lock_zoom_scale)
            except Exception as e:
                print("Error during unload:", e)
        self.canvas.removeEventFilter(self.event_filter)
