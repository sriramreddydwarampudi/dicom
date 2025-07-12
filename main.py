import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.utils import platform

import os
import traceback

# Try to import pydicom
try:
    import pydicom
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False

class DicomViewerApp(App):
    def build(self):
        self.title = "DICOM Viewer"
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title_label = Label(
            text='DICOM File Viewer',
            size_hint=(1, 0.1),
            font_size='20sp',
            bold=True
        )
        main_layout.add_widget(title_label)
        
        # File selection section
        file_section = BoxLayout(orientation='vertical', size_hint=(1, 0.3))
        
        file_label = Label(
            text='Select DICOM File:',
            size_hint=(1, 0.2),
            font_size='16sp'
        )
        file_section.add_widget(file_label)
        
        # File path display
        self.file_path_input = TextInput(
            text='No file selected',
            readonly=True,
            size_hint=(1, 0.4),
            multiline=False
        )
        file_section.add_widget(self.file_path_input)
        
        # Browse button
        browse_btn = Button(
            text='Browse Files',
            size_hint=(1, 0.4),
            font_size='16sp'
        )
        browse_btn.bind(on_press=self.open_file_chooser)
        file_section.add_widget(browse_btn)
        
        main_layout.add_widget(file_section)
        
        # X and Y input section
        xy_section = BoxLayout(orientation='vertical', size_hint=(1, 0.3))
        
        xy_label = Label(
            text='DICOM Coordinates:',
            size_hint=(1, 0.2),
            font_size='16sp'
        )
        xy_section.add_widget(xy_label)
        
        # X input
        x_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        x_layout.add_widget(Label(text='X:', size_hint=(0.2, 1)))
        self.x_input = TextInput(
            text='',
            size_hint=(0.8, 1),
            multiline=False,
            hint_text='X coordinate will appear here'
        )
        x_layout.add_widget(self.x_input)
        xy_section.add_widget(x_layout)
        
        # Y input
        y_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        y_layout.add_widget(Label(text='Y:', size_hint=(0.2, 1)))
        self.y_input = TextInput(
            text='',
            size_hint=(0.8, 1),
            multiline=False,
            hint_text='Y coordinate will appear here'
        )
        y_layout.add_widget(self.y_input)
        xy_section.add_widget(y_layout)
        
        main_layout.add_widget(xy_section)
        
        # Status section
        status_section = BoxLayout(orientation='vertical', size_hint=(1, 0.4))
        
        status_label = Label(
            text='DICOM Information:',
            size_hint=(1, 0.1),
            font_size='16sp'
        )
        status_section.add_widget(status_label)
        
        # Scrollable text area for DICOM info
        scroll = ScrollView()
        self.info_label = Label(
            text=self.get_initial_status(),
            text_size=(None, None),
            valign='top',
            font_size='12sp'
        )
        scroll.add_widget(self.info_label)
        status_section.add_widget(scroll)
        
        main_layout.add_widget(status_section)
        
        return main_layout
    
    def get_initial_status(self):
        if not PYDICOM_AVAILABLE:
            return ("PyDicom not available!\n\n"
                   "To install PyDicom in Pydroid3:\n"
                   "1. Open Pydroid3\n"
                   "2. Go to Menu (☰) → Pip\n"
                   "3. Type: pydicom\n"
                   "4. Tap Install\n\n"
                   "After installation, restart the app.")
        else:
            return "Ready to load DICOM files.\nSelect a file to view its information."
    
    def open_file_chooser(self, instance):
        if platform == 'android':
            # For Android, try to open in typical storage locations
            initial_path = '/storage/emulated/0/'
            if not os.path.exists(initial_path):
                initial_path = '/sdcard/'
            if not os.path.exists(initial_path):
                initial_path = '/'
        else:
            initial_path = '/'
        
        # Create file chooser popup
        content = BoxLayout(orientation='vertical')
        
        # File chooser
        filechooser = FileChooserListView(
            path=initial_path,
            filters=['*.dcm', '*.dicom', '*.DCM', '*.DICOM'],
            size_hint=(1, 0.8)
        )
        content.add_widget(filechooser)
        
        # Buttons
        button_layout = BoxLayout(size_hint=(1, 0.2))
        
        select_btn = Button(text='Select')
        cancel_btn = Button(text='Cancel')
        
        button_layout.add_widget(select_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)
        
        # Create popup
        popup = Popup(
            title='Choose DICOM File',
            content=content,
            size_hint=(0.9, 0.9)
        )
        
        def select_file(instance):
            if filechooser.selection:
                selected_file = filechooser.selection[0]
                self.file_path_input.text = selected_file
                self.load_dicom_file(selected_file)
                popup.dismiss()
        
        def cancel_selection(instance):
            popup.dismiss()
        
        select_btn.bind(on_press=select_file)
        cancel_btn.bind(on_press=cancel_selection)
        
        popup.open()
    
    def load_dicom_file(self, file_path):
        if not PYDICOM_AVAILABLE:
            self.info_label.text = "PyDicom not available. Please install it first."
            return
        
        try:
            # Load DICOM file
            ds = pydicom.dcmread(file_path)
            
            # Extract X and Y coordinates
            x_coord = ""
            y_coord = ""
            
            # Try to get image dimensions
            if hasattr(ds, 'Rows') and hasattr(ds, 'Columns'):
                y_coord = str(ds.Rows)
                x_coord = str(ds.Columns)
            
            # Try to get pixel spacing if available
            pixel_spacing_info = ""
            if hasattr(ds, 'PixelSpacing'):
                pixel_spacing_info = f"Pixel Spacing: {ds.PixelSpacing}\n"
            
            # Try to get image position if available
            position_info = ""
            if hasattr(ds, 'ImagePositionPatient'):
                position_info = f"Image Position: {ds.ImagePositionPatient}\n"
            
            # Try to get image orientation if available
            orientation_info = ""
            if hasattr(ds, 'ImageOrientationPatient'):
                orientation_info = f"Image Orientation: {ds.ImageOrientationPatient}\n"
            
            # Update input fields
            self.x_input.text = x_coord
            self.y_input.text = y_coord
            
            # Display comprehensive DICOM information
            info_text = f"File: {os.path.basename(file_path)}\n\n"
            info_text += f"Dimensions: {x_coord} x {y_coord}\n"
            info_text += pixel_spacing_info
            info_text += position_info
            info_text += orientation_info
            
            # Add basic DICOM tags
            info_text += "\nDICOM Tags:\n"
            info_text += f"Patient ID: {getattr(ds, 'PatientID', 'N/A')}\n"
            info_text += f"Study Date: {getattr(ds, 'StudyDate', 'N/A')}\n"
            info_text += f"Modality: {getattr(ds, 'Modality', 'N/A')}\n"
            info_text += f"Institution: {getattr(ds, 'InstitutionName', 'N/A')}\n"
            info_text += f"Manufacturer: {getattr(ds, 'Manufacturer', 'N/A')}\n"
            
            if hasattr(ds, 'SeriesDescription'):
                info_text += f"Series Description: {ds.SeriesDescription}\n"
            
            if hasattr(ds, 'SliceThickness'):
                info_text += f"Slice Thickness: {ds.SliceThickness}\n"
            
            self.info_label.text = info_text
            self.info_label.text_size = (None, None)
            
        except Exception as e:
            error_msg = f"Error loading DICOM file:\n{str(e)}\n\n"
            error_msg += "Traceback:\n" + traceback.format_exc()
            self.info_label.text = error_msg
            self.info_label.text_size = (None, None)
            
            # Clear input fields on error
            self.x_input.text = ""
            self.y_input.text = ""

if __name__ == '__main__':
    DicomViewerApp().run()
