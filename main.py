import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.utils import platform

import os
import traceback
import numpy as np
import matplotlib.pyplot as plt
import io

# Try to import pydicom
try:
    import pydicom
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False

class DicomViewerApp(App):
    def build(self):
        self.title = "DICOM Viewer"

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

        xy_label = Label(text='DICOM Coordinates:', size_hint=(1, 0.2), font_size='16sp')
        xy_section.add_widget(xy_label)

        x_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        x_layout.add_widget(Label(text='X:', size_hint=(0.2, 1)))
        self.x_input = TextInput(text='', size_hint=(0.8, 1), multiline=False)
        x_layout.add_widget(self.x_input)
        xy_section.add_widget(x_layout)

        y_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.4))
        y_layout.add_widget(Label(text='Y:', size_hint=(0.2, 1)))
        self.y_input = TextInput(text='', size_hint=(0.8, 1), multiline=False)
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
            size_hint_y=None
        )
        self.info_label.bind(texture_size=self.update_label_height)
        scroll.add_widget(self.info_label)
        status_section.add_widget(scroll)
        main_layout.add_widget(status_section)

        # Image display
        self.dicom_image = Image(size_hint=(1, 0.6))
        main_layout.add_widget(self.dicom_image)

        return main_layout

    def update_label_height(self, instance, value):
        self.info_label.height = self.info_label.texture_size[1]

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
            ds = pydicom.dcmread(file_path)

            x_coord = str(getattr(ds, 'Columns', ''))
            y_coord = str(getattr(ds, 'Rows', ''))
            self.x_input.text = x_coord
            self.y_input.text = y_coord

            pixel_spacing_info = ''
            real_x_mm = real_y_mm = ''
            if hasattr(ds, 'PixelSpacing') and x_coord and y_coord:
                spacing = ds.PixelSpacing
                pixel_spacing_info = f"Pixel Spacing: {spacing}\n"
                real_x_mm = float(x_coord) * float(spacing[1])
                real_y_mm = float(y_coord) * float(spacing[0])

            info_text = f"File: {os.path.basename(file_path)}\n\n"
            info_text += f"Dimensions: {x_coord} x {y_coord} pixels\n"
            if pixel_spacing_info:
                info_text += pixel_spacing_info
                info_text += f"Real Size: {real_x_mm:.2f} mm x {real_y_mm:.2f} mm\n"

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
                info_text += f"Slice Thickness: {ds.SliceThickness}\n"

            self.info_label.text = info_text

            # Show DICOM image
            if hasattr(ds, 'pixel_array'):
                try:
                    pixel_array = ds.pixel_array.astype(np.float32)
                    pixel_array -= pixel_array.min()
                    pixel_array /= pixel_array.max()
                    pixel_array *= 255.0
                    pixel_array = pixel_array.astype(np.uint8)

                    fig, ax = plt.subplots()
                    ax.imshow(pixel_array, cmap='gray')
                    ax.axis('off')
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
                    plt.close(fig)
                    buf.seek(0)
                    self.dicom_image.texture = CoreImage(buf, ext='png').texture
                except Exception as e:
                    self.info_label.text += f"\nImage Display Error: {str(e)}"

        except Exception as e:
            error_msg = f"Error loading DICOM file:\n{str(e)}\n\n"
            error_msg += "Traceback:\n" + traceback.format_exc()
            self.info_label.text = error_msg
            self.x_input.text = ''
            self.y_input.text = ''
            self.dicom_image.texture = None

if __name__ == '__main__':
    DicomViewerApp().run()
