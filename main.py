import kivy
kivy.require('2.3.0')

from kivy.config import Config
Config.set('graphics', 'multisamples', '0')  # Fixes rendering issues on some devices
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
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

import os
import traceback
import numpy as np
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
if platform != 'android':
    logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)

# Try to import pydicom
try:
    import pydicom
    PYDICOM_AVAILABLE = True
    logging.info("PyDicom imported successfully")
except ImportError:
    PYDICOM_AVAILABLE = False
    logging.error("PyDicom not available")

class DicomViewerApp(App):
    def build(self):
        logging.info("Building app interface")
        self.title = "DICOM Viewer"
        
        # Request Android permissions
        if platform == 'android':
            logging.info("Running on Android - requesting permissions")
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])

        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        title_label = Label(
            text='DICOM File Viewer',
            size_hint=(1, 0.1),
            font_size='20sp',
            bold=True
        )
        main_layout.add_widget(title_label)

        # File selection section
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

        main_layout.add_widget(file_section)

        # X and Y input section
        xy_section = BoxLayout(orientation='vertical', size_hint=(1, 0.2))

        xy_label = Label(text='DICOM Dimensions:', size_hint=(1, 0.2), font_size='16sp')
        xy_section.add_widget(xy_label)

        x_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        x_layout.add_widget(Label(text='Width:', size_hint=(0.2, 1)))
        self.x_input = TextInput(text='', size_hint=(0.8, 1), multiline=False, readonly=True)
        x_layout.add_widget(self.x_input)
        xy_section.add_widget(x_layout)

        y_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        y_layout.add_widget(Label(text='Height:', size_hint=(0.2, 1)))
        self.y_input = TextInput(text='', size_hint=(0.8, 1), multiline=False, readonly=True)
        y_layout.add_widget(self.y_input)
        xy_section.add_widget(y_layout)

        main_layout.add_widget(xy_section)

        # Status info
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
        main_layout.add_widget(status_section)

        # Image display
        self.dicom_image = Image(size_hint=(1, 0.6), allow_stretch=True)
        main_layout.add_widget(self.dicom_image)

        return main_layout

    def update_label_height(self, instance, value):
        instance.height = instance.texture_size[1]
        instance.text_size = (instance.width, None)

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
        initial_path = '/storage/emulated/0/' if platform == 'android' else '/'
        if not os.path.exists(initial_path):
            initial_path = '/sdcard/' if os.path.exists('/sdcard/') else '/'

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

        popup = Popup(title='Choose DICOM File', content=content, size_hint=(0.9, 0.9))

        def select_file(instance):
            if filechooser.selection:
                selected_file = filechooser.selection[0]
                self.file_path_input.text = selected_file
                # Schedule loading to avoid UI freeze
                Clock.schedule_once(lambda dt: self.load_dicom_file(selected_file))
                popup.dismiss()

        def cancel_selection(instance):
            popup.dismiss()

        select_btn.bind(on_press=select_file)
        cancel_btn.bind(on_press=cancel_selection)

        popup.open()

    def load_dicom_file(self, file_path):
        logging.info(f"Loading DICOM file: {file_path}")
        if not PYDICOM_AVAILABLE:
            self.info_label.text = "PyDicom not available. Please install it first."
            return

        try:
            # Clear previous image
            self.dicom_image.texture = None
            
            ds = pydicom.dcmread(file_path)
            logging.info(f"DICOM dataset loaded: {ds}")

            x_coord = str(getattr(ds, 'Columns', 'N/A'))
            y_coord = str(getattr(ds, 'Rows', 'N/A'))
            self.x_input.text = x_coord
            self.y_input.text = y_coord

            pixel_spacing_info = ''
            real_x_mm = real_y_mm = ''
            if hasattr(ds, 'PixelSpacing') and x_coord != 'N/A' and y_coord != 'N/A':
                spacing = ds.PixelSpacing
                pixel_spacing_info = f"Pixel Spacing: {spacing[0]} x {spacing[1]} mm\n"
                try:
                    real_x_mm = float(x_coord) * float(spacing[1])
                    real_y_mm = float(y_coord) * float(spacing[0])
                    pixel_spacing_info += f"Real Size: {real_x_mm:.2f} mm x {real_y_mm:.2f} mm\n"
                except:
                    logging.warning("Error calculating real dimensions")

            info_text = f"File: {os.path.basename(file_path)}\n\n"
            info_text += f"Dimensions: {x_coord} x {y_coord} pixels\n"
            info_text += pixel_spacing_info

            if hasattr(ds, 'ImagePositionPatient'):
                info_text += f"Image Position: {ds.ImagePositionPatient}\n"
            if hasattr(ds, 'ImageOrientationPatient'):
                info_text += f"Image Orientation: {ds.ImageOrientationPatient}\n"

            info_text += "\nDICOM Tags:\n"
            info_text += f"Patient ID: {getattr(ds, 'PatientID', 'N/A')}\n"
            info_text += f"Study Date: {getattr(ds, 'StudyDate', 'N/A')}\n"
            info_text += f"Modality: {getattr(ds, 'Modality', 'N/A')}\n"
            info_text += f"Institution: {getattr(ds, 'InstitutionName', 'N/A')}\n"
            info_text += f"Manufacturer: {getattr(ds, 'Manufacturer', 'N/A')}\n"
            if hasattr(ds, 'SeriesDescription'):
                info_text += f"Series Description: {ds.SeriesDescription}\n"
            if hasattr(ds, 'SliceThickness'):
                info_text += f"Slice Thickness: {ds.SliceThickness} mm\n"

            self.info_label.text = info_text

            # Show DICOM image
            if hasattr(ds, 'pixel_array'):
                try:
                    pixel_array = ds.pixel_array
                    logging.info(f"Pixel array shape: {pixel_array.shape}")
                    
                    # Normalize to 0-255
                    pixel_array = pixel_array.astype(np.float32)
                    pixel_array -= np.min(pixel_array)
                    pixel_array /= np.max(pixel_array)
                    pixel_array *= 255
                    pixel_array = pixel_array.astype(np.uint8)
                    
                    # Handle different pixel formats
                    if len(pixel_array.shape) == 2:
                        # Grayscale image
                        buf = pixel_array.tobytes()
                        texture = Texture.create(size=(pixel_array.shape[1], pixel_array.shape[0]), colorfmt='luminance')
                        texture.blit_buffer(buf, colorfmt='luminance', bufferfmt='ubyte')
                    else:
                        # Color image (uncommon in DICOM)
                        buf = pixel_array.tobytes()
                        texture = Texture.create(size=(pixel_array.shape[1], pixel_array.shape[0]), colorfmt='rgb')
                        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
                    
                    texture.flip_vertical()  # Correct orientation
                    self.dicom_image.texture = texture
                    logging.info("Image displayed successfully")
                    
                except Exception as e:
                    error_msg = f"Image Display Error: {str(e)}"
                    logging.error(error_msg)
                    self.info_label.text += f"\n{error_msg}"

        except Exception as e:
            error_msg = f"Error loading DICOM file:\n{str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            self.info_label.text = error_msg
            self.x_input.text = ''
            self.y_input.text = ''
            self.dicom_image.texture = None

if __name__ == '__main__':
    DicomViewerApp().run()
