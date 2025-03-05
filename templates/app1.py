import streamlit as st
import tensorflow as tf
from tensorflow.keras.models import load_model
import pyrebase
import numpy as np
from PIL import Image, ImageOps
import io

# 🔹 Firebase Configuration
firebaseConfig = {
    "apiKey": "AIzaSyBUc09vVr13lufna3PcRKIvkScJMmL84F8",
    "authDomain": "diabetic-retinopathy-d9ad0.firebaseapp.com",
    "databaseURL": "https://diabetic-retinopathy-d9ad0-default-rtdb.firebaseio.com",
    "projectId": "diabetic-retinopathy-d9ad0",
    "storageBucket": "diabetic-retinopathy-d9ad0.appspot.com",
    "messagingSenderId": "784479554899",
    "appId": "1:784479554899:web:741bb70f664687c789e5a6",
    "measurementId": "G-T9E5GHPJ65"
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# 🔹 Load Model with Streamlit Caching
@st.cache_resource
def load_trained_model():
    try:
        model_path = "C:\\Users\\rithi\\Downloads\\Diabetic_Retinopathy_Project\\Diabetic_Retinopathy_Project\\dr_weights.h5"
        model = load_model(model_path)
        st.success("✅ Model Loaded Successfully")
        return model
    except Exception as e:
        st.error(f"🚨 Error Loading Model: {e}")
        return None

model = load_trained_model()

# 🔹 Streamlit UI
st.title("Diabetic Retinopathy Diagnosis")

html_temp = """
    <div style="background:linear-gradient(to bottom, #66ccff 0%, #ff99cc 100%);padding:10px">
    <h1 style="color:white;text-align:center;"><em>EyeDR</em></h1>
    </div>
    <br></br>
"""
st.markdown(html_temp, unsafe_allow_html=True)

st.subheader("Eye Classification")
name = st.text_input("Enter Name")
file = st.file_uploader("Upload an Image", type=["jpg", "png", "jpeg"])

# 🔹 Function for Image Prediction
def import_and_predict(image_data, model):
    try:
        size = (224, 224)
        image = ImageOps.fit(image_data, size, Image.Resampling.LANCZOS)
        img_array = np.asarray(image)

        img_array = img_array / 255.0  # Normalize

        if img_array.shape[-1] == 4:
            img_array = img_array[..., :3]  # Remove Alpha Channel

        img_reshape = np.expand_dims(img_array, axis=0)  # Add batch dimension

        prediction = model.predict(img_reshape)

        st.write("📊 Model Raw Predictions:", prediction)

        return prediction
    except Exception as e:
        st.error(f"🚨 Error Processing Image: {e}")
        return None

if file is None:
    st.warning("⚠️ Please upload an image")
else:
    image = Image.open(file)
    st.image(image, use_column_width=True)
    
    if model is not None:
        prediction = import_and_predict(image, model)
        
        if prediction is not None:
            class_names = ["NO DR", "Mild DR", "Moderate DR", "Severe DR", "Proliferative DR"]
            dr = class_names[np.argmax(prediction)]
            confidence_score = np.max(prediction) * 100  # Convert to percentage
            
            st.write(f"🔢 Prediction Index: {np.argmax(prediction)}")
            st.write(f"🎯 Confidence Score: {confidence_score:.2f}%")

            # 🔹 Store in Firebase (Only if Name is Provided)
            if name.strip():
                try:
                    db.child("Patients").child(name).update({"diabetic_retinopathy": dr, "confidence": confidence_score})
                    st.success(f"✅ Diagnosis: {dr}")
                except Exception as e:
                    st.error(f"🚨 Firebase Error: {e}")
            else:
                st.warning("⚠️ Please enter a name to save the result in Firebase.")

            # 🔹 Function to Generate Report
            def generate_report(name, diagnosis, confidence):
                if not name.strip():
                    return "⚠️ Error: Name is required for report generation."
                
                # Save Report Date in Session State
                if "report_date" not in st.session_state:
                    st.session_state["report_date"] = str(st.date_input("Select Report Date"))

                report_text = f"""
                📌 **Diabetic Retinopathy Report**
                --------------------------------------
                👤 **Patient Name:** {name}
                🏥 **Diagnosis:** {diagnosis}
                🎯 **Confidence Score:** {confidence:.2f}%
                🕒 **Generated on:** {st.session_state["report_date"]}
                ✅ This report was generated by EyeDR, an AI-based system for detecting Diabetic Retinopathy.
                """
                return report_text

            # 🔹 Generate Report
            report = generate_report(name, dr, confidence_score)

            # 🔹 Fix Report Download (Save as PDF)
            def save_report_as_pdf(report_text, filename):
                from fpdf import FPDF
                
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                for line in report_text.split("\n"):
                    pdf.cell(200, 10, txt=line, ln=True, align="L")

                pdf_output = io.BytesIO()
                pdf.output(pdf_output, 'F')
                pdf_output.seek(0)

                return pdf_output

            # Convert Report to PDF
            report_pdf = save_report_as_pdf(report, f"{name}_Diagnosis_Report.pdf")

            # 🔹 Download Report Button
            st.download_button(
                label="📥 Download Report",
                data=report_pdf,
                file_name=f"{name}_Diagnosis_Report.pdf",
                mime="application/pdf"
            )
