#!/usr/bin/env python3
"""
DICOM Viewer Application with Android Support
"""

import sys
import os
from os.path import join, basename
from android.storage import app_storage_path

# --- Dependency Management Section ---
# Add install directory to path
target = join(app_storage_path(), 'python')
if target not in sys.path:
    sys.path.append(target)

def ensure_dependencies():
    """Install missing packages at runtime if needed"""
    missing = []
    required = [
        'kivy', 
        'pydicom', 
        'numpy',
        'matplotlib',
        'PIL'  # Pillow package
    ]
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing packages: {missing}, attempting install...")
        try:
            import subprocess
            subprocess.run([
                sys.executable, 
                '-m', 'pip', 
                'install', 
                '--target', target,
                *missing
            ], check=True)
            print("Installation completed")
            # Refresh imports
            for package in missing:
                __import__(package)
        except Exception as e:
            print(f"Install failed: {e}")
            raise

ensure_dependencies()

# --- Main Imports ---
import kivy
kivy.require('2.3.0')

from kivy.config import Config
Config.set('graphics', 'multisamples', '0')  # Fixes rendering issues
Config.set('kivy', 'log_level', 'warning')   # Reduce log spam

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp

import numpy as np
import logging
import traceback
from io import BytesIO

# --- DICOM Setup ---
try:
    import pydicom
    from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False

# --- Logging Configuration ---
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
if platform != 'android':
    logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)

class DicomViewerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ds = None  # Will hold the DICOM dataset
        self.file_path = ""
        self.title = "DICOM Viewer"

    def build(self):
        """Build the application interface"""
        logging.info("Building app interface")
        
        # Request Android permissions
        if platform == 'android':
            self.request_android_permissions()

        # Main layout container
        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        # Add all UI components
        self.create_title(main_layout)
        self.create_file_section(main_layout)
        self.create_dimension_section(main_layout)
        self.create_info_section(main_layout)
        self.create_image_display(main_layout)

        return main_layout

    def request_android_permissions(self):
        """Request required Android permissions"""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])
            logging.info("Android permissions requested")
        except Exception as e:
            logging.error(f"Permission request failed: {e}")

    def create_title(self, parent):
        """Create title label"""
        title_label = Label(
            text=self.title,
            size_hint=(1, 0.1),
            font_size='20sp',
            bold=True
        )
        parent.add_widget(title_label)

    def create_file_section(self, parent):
        """Create file selection section"""
        file_section = BoxLayout(orientation='vertical', size_hint=(1, 0.2))
        
        file_label = Label(text='Select DICOM File:', size_hint=(1, 0.2), font_size='16sp')
        file_section.add_widget(file_label)

        self.file_path_input = TextInput(
            text='No file selected',
            readonly=True,
            size_hint=(1, 0.4),
            multiline=False
        )
        file_section.add_widget(self.file_path_input)

        browse_btn = Button(text='Browse Files', size_hint=(1, 0.4), font_size='16sp')
        browse_btn.bind(on_press=self.open_file_chooser)
        file_section.add_widget(browse_btn)

        parent.add_widget(file_section)

    def create_dimension_section(self, parent):
        """Create dimension display section"""
        xy_section = BoxLayout(orientation='vertical', size_hint=(1, 0.2))

        xy_label = Label(text='DICOM Dimensions:', size_hint=(1, 0.2), font_size='16sp')
        xy_section.add_widget(xy_label)

        # Width display
        x_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        x_layout.add_widget(Label(text='Width:', size_hint=(0.2, 1)))
        self.x_input = TextInput(text='', size_hint=(0.8, 1), multiline=False, readonly=True)
        x_layout.add_widget(self.x_input)
        xy_section.add_widget(x_layout)

        # Height display
        y_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        y_layout.add_widget(Label(text='Height:', size_hint=(0.2, 1)))
        self.y_input = TextInput(text='', size_hint=(0.8, 1), multiline=False, readonly=True)
        y_layout.add_widget(self.y_input)
        xy_section.add_widget(y_layout)

        parent.add_widget(xy_section)

    def create_info_section(self, parent):
        """Create DICOM info display section"""
        status_section = BoxLayout(orientation='vertical', size_hint=(1, 0.3))
        status_label = Label(text='DICOM Information:', size_hint=(1, 0.1), font_size='16sp')
        status_section.add_widget(status_label)

        scroll = ScrollView(size_hint=(1, 0.9))
        self.info_label = Label(
            text=self.get_initial_status(),
            text_size=(None, None),
            valign='top',
            font_size='12sp',
            size_hint_y=None,
            halign='left'
        )
        self.info_label.bind(texture_size=self.update_label_height)
        scroll.add_widget(self.info_label)
        status_section.add_widget(scroll)
        parent.add_widget(status_section)

    def create_image_display(self, parent):
        """Create image display section"""
        self.dicom_image = Image(
            size_hint=(1, 0.6), 
            allow_stretch=True,
            keep_ratio=True
        )
        parent.add_widget(self.dicom_image)

    def update_label_height(self, instance, value):
        """Adjust label height based on content"""
        instance.height = instance.texture_size[1]
        instance.text_size = (instance.width, None)

    def get_initial_status(self):
        """Return initial status message"""
        if not PYDICOM_AVAILABLE:
            return ("PyDicom not available!\n\n"
                   "The app will attempt to install it automatically.\n"
                   "If installation fails, please install manually.")
        return "Ready to load DICOM files.\nSelect a file to begin."

    def open_file_chooser(self, instance):
        """Open file selection dialog"""
        initial_path = self.get_initial_path()
        
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(
            path=initial_path,
            filters=['*.dcm', '*.dicom', '*.DCM', '*.DICOM'],
            size_hint=(1, 0.8)
        )
        content.add_widget(filechooser)

        button_layout = BoxLayout(size_hint=(1, 0.2))
        select_btn = Button(text='Select')
        cancel_btn = Button(text='Cancel')
        button_layout.add_widget(select_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)

        popup = Popup(
            title='Choose DICOM File', 
            content=content, 
            size_hint=(0.9, 0.9)
        )

        select_btn.bind(on_press=lambda x: self.on_file_selected(filechooser, popup))
        cancel_btn.bind(on_press=popup.dismiss)

        popup.open()

    def get_initial_path(self):
        """Get appropriate initial path for file chooser"""
        if platform == 'android':
            paths_to_try = [
                '/storage/emulated/0/',
                '/sdcard/',
                '/'
            ]
            for path in paths_to_try:
                if os.path.exists(path):
                    return path
        return '/'

    def on_file_selected(self, filechooser, popup):
        """Handle file selection"""
        if filechooser.selection:
            selected_file = filechooser.selection[0]
            self.file_path_input.text = selected_file
            Clock.schedule_once(lambda dt: self.load_dicom_file(selected_file))
            popup.dismiss()

    def load_dicom_file(self, file_path):
        """Load and display DICOM file"""
        if not PYDICOM_AVAILABLE:
            self.show_error("PyDicom not available")
            return

        try:
            self.reset_display()
            self.file_path = file_path
            
            # Read DICOM file
            self.ds = pydicom.dcmread(file_path)
            logging.info(f"DICOM dataset loaded: {self.ds}")

            # Update basic info
            self.update_basic_info()
            
            # Display DICOM tags
            self.update_dicom_tags()
            
            # Display image
            if hasattr(self.ds, 'pixel_array'):
                self.display_dicom_image()

        except Exception as e:
            self.handle_load_error(e)

    def reset_display(self):
        """Reset all display elements"""
        self.ds = None
        self.x_input.text = ''
        self.y_input.text = ''
        self.dicom_image.texture = None

    def update_basic_info(self):
        """Update basic DICOM information"""
        # Get dimensions
        x_coord = str(getattr(self.ds, 'Columns', 'N/A'))
        y_coord = str(getattr(self.ds, 'Rows', 'N/A'))
        self.x_input.text = x_coord
        self.y_input.text = y_coord

        # Calculate pixel spacing if available
        pixel_spacing_info = ''
        if hasattr(self.ds, 'PixelSpacing') and x_coord != 'N/A' and y_coord != 'N/A':
            spacing = self.ds.PixelSpacing
            pixel_spacing_info = f"Pixel Spacing: {spacing[0]} x {spacing[1]} mm\n"
            try:
                real_x_mm = float(x_coord) * float(spacing[1])
                real_y_mm = float(y_coord) * float(spacing[0])
                pixel_spacing_info += f"Real Size: {real_x_mm:.2f} mm x {real_y_mm:.2f} mm\n"
            except:
                logging.warning("Error calculating real dimensions")

        # Build info text
        info_text = f"File: {basename(self.file_path)}\n\n"
        info_text += f"Dimensions: {x_coord} x {y_coord} pixels\n"
        info_text += pixel_spacing_info

        # Add position/orientation if available
        if hasattr(self.ds, 'ImagePositionPatient'):
            info_text += f"Image Position: {self.ds.ImagePositionPatient}\n"
        if hasattr(self.ds, 'ImageOrientationPatient'):
            info_text += f"Image Orientation: {self.ds.ImageOrientationPatient}\n"

        self.info_label.text = info_text

    def update_dicom_tags(self):
        """Update DICOM tag information"""
        if not self.ds:
            return

        tags_text = "\nDICOM Tags:\n"
        tags_text += f"Patient ID: {getattr(self.ds, 'PatientID', 'N/A')}\n"
        tags_text += f"Study Date: {getattr(self.ds, 'StudyDate', 'N/A')}\n"
        tags_text += f"Modality: {getattr(self.ds, 'Modality', 'N/A')}\n"
        tags_text += f"Institution: {getattr(self.ds, 'InstitutionName', 'N/A')}\n"
        tags_text += f"Manufacturer: {getattr(self.ds, 'Manufacturer', 'N/A')}\n"
        
        if hasattr(self.ds, 'SeriesDescription'):
            tags_text += f"Series Description: {self.ds.SeriesDescription}\n"
        if hasattr(self.ds, 'SliceThickness'):
            tags_text += f"Slice Thickness: {self.ds.SliceThickness} mm\n"

        self.info_label.text += tags_text

    def display_dicom_image(self):
        """Display the DICOM pixel array as an image"""
        try:
            pixel_array = self.ds.pixel_array
            
            # Apply DICOM-specific processing
            processed_array = self.process_dicom_image(pixel_array)
            if processed_array is None:
                return

            # Create texture from numpy array
            texture = self.array_to_texture(processed_array)
            if texture:
                self.dicom_image.texture = texture
                logging.info("Image displayed successfully")

        except Exception as e:
            self.show_error(f"Image display error: {str(e)}")
            logging.error(traceback.format_exc())

    def process_dicom_image(self, pixel_array):
        """Process DICOM pixel array for display"""
        try:
            # Apply DICOM-specific transformations
            if hasattr(self.ds, 'WindowWidth') and hasattr(self.ds, 'WindowCenter'):
                pixel_array = apply_voi_lut(pixel_array, self.ds)
            elif hasattr(self.ds, 'RescaleSlope') and hasattr(self.ds, 'RescaleIntercept'):
                pixel_array = pixel_array * float(self.ds.RescaleSlope) + float(self.ds.RescaleIntercept)

            # Normalize to 8-bit range
            pixel_array = pixel_array.astype(np.float32)
            pixel_array -= np.min(pixel_array)
            pixel_array /= np.max(pixel_array)
            pixel_array = (pixel_array * 255).astype(np.uint8)

            return pixel_array

        except Exception as e:
            logging.error(f"Image processing error: {e}")
            return None

    def array_to_texture(self, array):
        """Convert numpy array to Kivy texture"""
        try:
            if len(array.shape) == 2:  # Grayscale
                buf = array.tobytes()
                texture = Texture.create(
                    size=(array.shape[1], array.shape[0]), 
                    colorfmt='luminance'
                )
                texture.blit_buffer(buf, colorfmt='luminance', bufferfmt='ubyte')
            else:  # Color (unlikely in DICOM)
                buf = array.tobytes()
                texture = Texture.create(
                    size=(array.shape[1], array.shape[0]), 
                    colorfmt='rgb'
                )
                texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

            texture.flip_vertical()  # Correct orientation
            return texture

        except Exception as e:
            logging.error(f"Texture creation error: {e}")
            return None

    def handle_load_error(self, error):
        """Handle DICOM loading errors"""
        error_msg = f"Error loading DICOM file:\n{str(error)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        self.show_error(error_msg)
        self.reset_display()

    def show_error(self, message):
        """Display error message"""
        self.info_label.text = message
        self.x_input.text = ''
        self.y_input.text = ''
        self.dicom_image.texture = None

if __name__ == '__main__':
    DicomViewerApp().run()
