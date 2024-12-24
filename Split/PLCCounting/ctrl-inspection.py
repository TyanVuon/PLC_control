
import os  # For directory operations
import time  # For time delays
import serial  # For serial communication
import cv2  # For camera operations
from tqdm import tqdm  # For progress bars
import shutil  # For file operations
import torch  # For PyTorch operations
import numpy as np  # For numerical operations
import streamlit as st  # For the web interface
from datetime import datetime  # For timestamping
from scipy.special import softmax  # For softmax operations
from scipy.ndimage import label, center_of_mass  # For image processing
from datasets import Dataset, Image  # For loading datasets
from transformers import AutoImageProcessor, UperNetForSemanticSegmentation 



# =========================
# SerialAppManager Singleton
# =========================

# (Include the SerialAppManager class here as defined above)

# =========================
# Inspection Functions
# =========================

# Constants for Inspection
DATA_PATH = "data"
MODEL_PATH = "model"
SAVE_PATH = "results"
os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(os.path.join(SAVE_PATH, "true_positive"), exist_ok=True)
os.makedirs(os.path.join(SAVE_PATH, "true_negative"), exist_ok=True)
os.makedirs(os.path.join(SAVE_PATH, "false_positive"), exist_ok=True)
os.makedirs(os.path.join(SAVE_PATH, "false_negative"), exist_ok=True)

# Set up device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Set wide layout first
st.set_page_config(layout="wide")

# Load image processor and model
@st.cache_resource
def load_model():
    image_processor = AutoImageProcessor.from_pretrained(MODEL_PATH)
    model = UperNetForSemanticSegmentation.from_pretrained(MODEL_PATH, num_labels=2, ignore_mismatched_sizes=True).to(device)
    return image_processor, model

image_processor, model = load_model()

# Load dataset
@st.cache_data
def load_dataset():
    image_paths = []
    for root, _, files in os.walk(DATA_PATH):
        for filename in files:
            if filename.endswith('.png') and '_GT' not in filename:
                image_path = os.path.join(root, filename)
                image_paths.append(image_path)
    
    dataset = Dataset.from_dict({"pixel_values": image_paths}).cast_column("pixel_values", Image())
    return dataset

dataset = load_dataset()

# Inference image
def inference_image(example):
    # Load image
    image = example["pixel_values"]
    image_path = image.filename
    image_name = os.path.basename(image_path).split(".")[0] 

    # Preprocess and inference
    processed_image = image_processor(image, return_tensors="pt").to(device)
    with torch.no_grad():
        logits = model(**processed_image).logits.detach().cpu().numpy().squeeze()
        predictions = logits.argmax(axis=0)
        probabilities = softmax(logits, axis=0)[1]

    # Resize image for visualization
    image = image.resize((image_processor.size["width"], image_processor.size["height"]))

    return predictions, probabilities, image, image_path, image_name

# Analyze defect properties
def analyze_defects(predictions):
    # Pixel to mm² conversion factor
    PIXEL_TO_MM2 = 0.001296
    
    labeled_array, num_features = label(predictions)
    defect_properties = []

    for label_id in range(1, num_features + 1):
        defect_mask = (labeled_array == label_id)
        defect_area_pixels = np.sum(defect_mask)
        defect_area_mm2 = defect_area_pixels * PIXEL_TO_MM2  # Convert to mm²
        defect_centroid = center_of_mass(defect_mask)
        defect_properties.append({
            "Defect ID": label_id,
            "Area (mm²)": defect_area_mm2,
            "Area (pixels)": defect_area_pixels,  # Keep pixels for reference
            "Centroid (y, x)": defect_centroid
        })

    return defect_properties

# Function to display colored probability
def display_probability(probability):
    # Create container for custom styling
    prob_container = st.container()
    
    with prob_container:
        if probability > 0.5:
            st.markdown(
                f"""
                <div style="
                    padding: 10px;
                    border-radius: 5px;
                    background-color: rgba(255, 0, 0, 0.1);
                    border: 1px solid red;
                ">
                    <h3 style="color: red; margin: 0;">
                        Defect Probability: {probability:.4f}
                    </h3>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="
                    padding: 10px;
                    border-radius: 5px;
                    background-color: rgba(0, 255, 0, 0.1);
                    border: 1px solid green;
                ">
                    <h3 style="color: green; margin: 0;">
                        Defect Probability: {probability:.4f}
                    </h3>
                </div>
                """,
                unsafe_allow_html=True
            )

def create_folder(product_id, username, current_time):
    folder_name = f"{product_id}_{username}_{current_time}"
    folder_path = os.path.join(SAVE_PATH, folder_name)
    
    # Create main folder
    os.makedirs(folder_path, exist_ok=True)
    
    # Create subfolders
    subfolders = [f"layer {i+1}" for i in range(11)]
    for subfolder in subfolders:
        os.makedirs(os.path.join(folder_path, subfolder), exist_ok=True)
    
    return folder_path

def safe_delete(file_path):
    """Safely delete a file with proper error handling"""
    try:
        if os.path.exists(file_path):
            os.chmod(file_path, 0o666)  # Give read/write permission
            os.remove(file_path)
            return True
    except Exception as e:
        st.error(f"Error deleting file {file_path}: {str(e)}")
        return False

def show_saved_files(folder):
    """Show and manage saved files"""
    if os.path.exists(folder):
        files = [f for f in os.listdir(folder) if f.endswith((".png"))]
        if files:
            st.markdown("### Saved Files")
            for file in files:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(file)
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{file}"):
                        file_path = os.path.join(folder, file)
                        if safe_delete(file_path):
                            st.success(f"Deleted {file}")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete {file}. You may need to delete manually using sudo.")

# Add new CameraUtility class
class CameraUtility:
    def __init__(self, device_path='/dev/video0'):
        self.device_path = device_path
        self.cap = None
        
    def initialize(self):
        """Initialize camera connection"""
        try:
            self.cap = cv2.VideoCapture(self.device_path)
            if not self.cap.isOpened():
                raise Exception(f"Failed to open camera at {self.device_path}")
            
            # Get camera properties
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            print(f"Camera initialized - Resolution: {self.width}x{self.height}, FPS: {self.fps}")
            return True
        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            return False

    def get_frame(self):
        """Get a single frame from the camera"""
        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                # Convert BGR to RGB for streamlit
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None

    def release(self):
        """Release camera resources"""
        if self.cap:
            self.cap.release()

# =========================
# SerialAppManager Singleton
# =========================

class SerialAppManager:
    def __init__(self, port_name='/dev/ttyUSB0'):
        self.serial_controller = SerialController(port_name=port_name)
        self.camera_controller = CameraController()
        self.command_handler = CommandHandler(self.serial_controller, self.camera_controller)
        
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def run(self):
        while self.running:
            command, layer, sections = self.serial_controller.read_data()
            if command:
                self.command_handler.process_incoming_command(command, layer, sections)
            time.sleep(0.1)  # Adjust as needed
    
    def send_command(self, data):
        self.serial_controller.write_data(data)
    
    def get_latest_status(self):
        return self.command_handler.current_layer_index, self.command_handler.current_section_count
    
    def stop(self):
        self.running = False
        self.thread.join()
        self.serial_controller.close()
        self.camera_controller.release()

@st.experimental_singleton
def get_serial_manager():
    return SerialAppManager(port_name='/dev/ttyUSB0')

# =========================
# Streamlit App Functions
# =========================

def control_panel(manager: SerialAppManager):
    st.header("Control Panel")
    
    st.markdown("### Send Commands")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Send READY (300)", key="ready_btn"):
            manager.send_command(300)
            st.success("Sent READY signal (300) to PLC.")
    
    with col2:
        if st.button("Send DONE (500)", key="done_btn"):
            manager.send_command(500)
            st.success("Sent DONE signal (500) to PLC.")
    
    with col3:
        if st.button("Send EXIT (700)", key="exit_btn"):
            manager.send_command(700)
            st.success("Sent EXIT signal (700) to PLC.")
            manager.stop()
            st.stop()
    
    st.markdown("---")
    
    st.markdown("### Serial Communication Status")
    latest_layer, latest_sections = manager.get_latest_status()
    st.write(f"**Current Layer:** {latest_layer}")
    st.write(f"**Current Sections:** {latest_sections}")

def inspection_app(manager: SerialAppManager):
    st.header("Image Inspection")
    
    # Initialize session state variables
    if "state" not in st.session_state:
        st.session_state.state = "preparation"
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "save_folder" not in st.session_state:
        st.session_state.save_folder = None

    # Navigation
    if st.session_state.state == "preparation":
        preparation_state(manager)
    elif st.session_state.state == "photograph":
        photograph_stage(manager)
    elif st.session_state.state == "inspection":
        inspection_state()

def preparation_state(manager: SerialAppManager):
    st.title("カメラ設定")
    
    # Initialize camera if not already done
    if "camera" not in st.session_state:
        st.session_state.camera = CameraUtility()
        if not st.session_state.camera.initialize():
            st.error("カメラの初期化に失敗しました")
            return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create placeholder for camera feed
        camera_feed = st.empty()
        
        # Update camera feed
        frame = st.session_state.camera.get_frame()
        if frame is not None:
            camera_feed.image(frame, channels="RGB", use_container_width=True)
        
    with col2:
        st.markdown("""
            ### 設定手順
            1. 画面上の十字と画像の中心が重なるように、カメラを調整してください。
            2. 製品番号を入力してください。
            3. 検査担当者を入力してください。
            4. 上記の3つの項目を確認した上で、「準備完了」ボタンをクリックしてください。
        """)
        
        # Display current time
        current_time = datetime.now().strftime("%Y-%m-%d-%H-%M")
        st.markdown(f"### 現在時刻\n**{current_time}**")
        
        # Input fields
        st.markdown("### 基本情報")
        num_id = 12
        product_id = st.text_input("製品番号", 
                                 max_chars=num_id,
                                 help=f"製品番号（{num_id}桁）を入力してください")
        
        username = st.text_input("検査担当者",
                               help="検査担当者を入力してください")
        
        # Validation
        is_valid = (len(product_id) == num_id and username)
        
        if is_valid:
            if st.button("準備完了", type="primary", use_container_width=True):
                folder_path = create_folder(product_id, username, current_time)
                st.success(f"検査フォルダを作成しました：{folder_path}")
                st.session_state.save_folder = folder_path
                st.session_state.state = "photograph"
                st.rerun()
        else:
            if product_id and username:
                st.warning(f"{num_id}桁の製品番号を入力してください")

def photograph_stage(manager: SerialAppManager):
    st.title("カメラ撮影")
        
    # Initialize image counter if not present
    if "img_num" not in st.session_state:
        st.session_state.img_num = 1
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create placeholder for camera feed
        camera_feed = st.empty()
        
        # Update camera feed
        frame = st.session_state.camera.get_frame()
        if frame is not None:
            camera_feed.image(frame, channels="RGB", use_container_width=True)
    
    with col2:
        st.markdown("""
            ### 撮影手順
            1. 撮影開始前、レイヤー番号を入力してください。
            2. 撮影完了後、「撮影完了」ボタンをクリックしてください。
        """)
        
        # Display current time
        current_time = datetime.now().strftime("%Y-%m-%d-%H-%M")
        st.markdown(f"### 現在時刻\n**{current_time}**")
        
        # Input fields
        num_ly = 11
        layer_num = st.text_input("レイヤー番号", 
                                max_chars=2,
                                help=f"レイヤー番号（1~{num_ly}）を入力してください")
        
        # Validate layer number
        try:
            layer_num_int = int(layer_num)
            is_valid = (1 <= layer_num_int <= num_ly)
        except ValueError:
            is_valid = False
        
        if layer_num:  # Only show validation message if user has entered something
            if not is_valid:
                st.warning(f"レイヤー数は1～{num_ly}の数値で入力してください。")
        
        # Capture photo button
        if is_valid and st.session_state.save_folder:
            if st.button("📸 撮影", use_container_width=True):
                layer_folder = os.path.join(st.session_state.save_folder, f"layer {layer_num}")
                os.makedirs(layer_folder, exist_ok=True)
                
                image_path = os.path.join(layer_folder, f"layer{layer_num}_img{st.session_state.img_num}.png")
                st.session_state.img_num += 1
                frame = st.session_state.camera.get_frame()

                if frame is not None:
                    # Save file
                    cv2.imwrite(image_path, frame)
                
                    # Set permissions after saving
                    os.chmod(image_path, 0o666)

                    st.success(f"画像を保存しました： {image_path}")
                else:
                    st.error("画像の保存に失敗しました")
            
            # Complete button
            if st.button("撮影完了", type="primary", use_container_width=True):
                st.session_state.state = "inspection"
                # Release camera before moving to inspection
                st.session_state.camera.release()
                st.rerun()

    # Show saved files
    st.divider()
    if st.session_state.save_folder:
        layer_folder = os.path.join(st.session_state.save_folder, f"layer {layer_num}" if is_valid else "")
        if os.path.exists(layer_folder):
            show_saved_files(layer_folder)

def inspection_state():
    st.title("Image Inspection")
    
    # Add quit button at the top right
    _, quit_col2 = st.columns([6, 1])
    with quit_col2:
        if st.button("🚪 Quit Inspection", type="primary", use_container_width=True):
            st.success("Inspection session ended. Thank you!")
            st.stop()
    
    # Display progress information
    total_images = len(dataset)
    current_image = st.session_state.current_index + 1
    
    with st.container():
        st.progress(current_image / total_images)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Image", f"{current_image}")
        with col2:
            st.metric("Total Images", f"{total_images}")
        with col3:
            st.metric("Progress", f"{(current_image / total_images * 100):.1f}%")

    example = dataset[st.session_state.current_index]
    predictions, probabilities, image, image_path, image_name = inference_image(example)

    st.subheader(f"Image: {image_name}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.image(image, caption="Original Image", use_container_width=True)
    with col2:
        st.image(probabilities, caption="Defect Probability Heatmap", use_container_width=True)

    display_probability(np.max(probabilities))
    
    defect_properties = analyze_defects(predictions)
    if defect_properties:
        st.divider()
        
        # Calculate total defect area in mm²
        total_defect_area_mm2 = sum(defect['Area (mm²)'] for defect in defect_properties)
        
        # Add defect evaluation
        st.markdown("### Defect Evaluation")
        eval_col1, eval_col2, eval_col3 = st.columns(3)
        
        # Check condition 1: Single defect > 0.05 mm²
        has_medium_defect = any(defect['Area (mm²)'] > 0.05 for defect in defect_properties)
        with eval_col1:
            if has_medium_defect:
                st.markdown("""
                    <div style='padding: 10px; background-color: rgba(255, 0, 0, 0.1); 
                            border-left: 5px solid red; margin: 5px 0;'>
                        <span style='color: red;'>✗ Single defect > 0.05 mm² detected</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style='padding: 10px; background-color: rgba(0, 255, 0, 0.1); 
                            border-left: 5px solid green; margin: 5px 0;'>
                        <span style='color: green;'>✓ No defect > 0.05 mm²</span>
                    </div>
                """, unsafe_allow_html=True)
        
        # Check condition 2: Single defect > 0.2 mm²
        has_large_defect = any(defect['Area (mm²)'] > 0.2 for defect in defect_properties)
        with eval_col2:
            if has_large_defect:
                st.markdown("""
                    <div style='padding: 10px; background-color: rgba(255, 0, 0, 0.1); 
                            border-left: 5px solid red; margin: 5px 0;'>
                        <span style='color: red;'>✗ Single defect > 0.2 mm² detected</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style='padding: 10px; background-color: rgba(0, 255, 0, 0.1); 
                            border-left: 5px solid green; margin: 5px 0;'>
                        <span style='color: green;'>✓ No defect > 0.2 mm²</span>
                    </div>
                """, unsafe_allow_html=True)
        
        # Check condition 3: Total defect > 0.3 mm²
        with eval_col3:
            if total_defect_area_mm2 > 0.3:
                st.markdown(f"""
                    <div style='padding: 10px; background-color: rgba(255, 0, 0, 0.1); 
                            border-left: 5px solid red; margin: 5px 0;'>
                        <span style='color: red;'>✗ Total defect area: {total_defect_area_mm2:.3f} mm²</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style='padding: 10px; background-color: rgba(0, 255, 0, 0.1); 
                            border-left: 5px solid green; margin: 5px 0;'>
                        <span style='color: green;'>✓ Total defect area: {total_defect_area_mm2:.3f} mm²</span>
                    </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # Display individual defect properties with colored warnings
        for defect in defect_properties:
            with st.container():
                cols = st.columns(3)
                # Defect ID column
                cols[0].markdown(f"**Defect #{defect['Defect ID']}**")
                
                # Area column with color coding
                area_mm2 = defect['Area (mm²)']
                if area_mm2 > 0.2:
                    cols[1].markdown(f"""
                        <div style='color: red;'>
                            Area: {area_mm2:.3f} mm² ⚠️⚠️
                        </div>
                    """, unsafe_allow_html=True)
                elif area_mm2 > 0.05:
                    cols[1].markdown(f"""
                        <div style='color: red;'>
                            Area: {area_mm2:.3f} mm² ⚠️
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    cols[1].markdown(f"Area: {area_mm2:.3f} mm²")
                
                # Location column
                y, x = defect['Centroid (y, x)']
                cols[2].markdown(f"Location: ({x:.1f}, {y:.1f})")
            st.divider()
    else:
        st.info("No defects detected in this image")

    user_choice = st.radio("Select Classification", ["", "Defect", "Good"], key=f"radio_{st.session_state.current_index}")

    if user_choice:
        model_prediction = 1 if np.any(predictions == 1) else 0
        user_choice_value = 1 if user_choice == "Defect" else 0

        folder = ""
        if user_choice_value == model_prediction:
            folder = "true_positive" if user_choice_value == 1 else "true_negative"
        else:
            folder = "false_positive" if user_choice_value == 1 else "false_negative"

        # Use the created folder path
        dest_folder = os.path.join("results", folder)
        os.makedirs(dest_folder, exist_ok=True)
        shutil.copy(image_path, dest_folder)
        st.write(f"Moved {image_name} to {dest_folder}")

    if user_choice != "":
        if st.button("Next", use_container_width=True):
            if st.session_state.current_index < len(dataset) - 1:
                st.session_state.current_index += 1
                st.rerun()
            else:
                st.write("Inspection finished!")
                st.stop()
    else:
        st.write("Please make a classification choice before proceeding to next image.")

def image_inspection():
    # Initialize session state variables
    if "state" not in st.session_state:
        st.session_state.state = "preparation"
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "save_folder" not in st.session_state:
        st.session_state.save_folder = None

    # Route to appropriate state
    if st.session_state.state == "preparation":
        preparation_state(get_serial_manager())
    elif st.session_state.state == "photograph":
        photograph_stage(get_serial_manager())
    else:
        inspection_state()

# =========================
# Streamlit App Main Function
# =========================

def main_app():
    st.sidebar.title("App Navigation")
    app_mode = st.sidebar.radio("Choose the app mode",
                                ["Control Panel", "Image Inspection"])
    
    manager = get_serial_manager()
    
    if app_mode == "Control Panel":
        control_panel(manager)
    elif app_mode == "Image Inspection":
        image_inspection()

#if __name__ == "__main__":
main_app()
