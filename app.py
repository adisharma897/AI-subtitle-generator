from flask import Flask, render_template, request, redirect, jsonify
from faster_whisper import WhisperModel
import os
from werkzeug.utils import secure_filename
import ffmpeg
import math

app = Flask(__name__)

# Configure upload folder and allowed file extensions
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_audio(input_video_name):
    extracted_audio = input_video_name.rsplit('.', 1)[0] + ".wav"
    
    stream = ffmpeg.input(input_video_name)
    stream = ffmpeg.output(stream, extracted_audio)
    ffmpeg.run(stream, overwrite_output=True)
    print(f"Extracted audio from {input_video_name} to {extracted_audio}")
    return extracted_audio

def transcribe(audio):
    model = WhisperModel("small")
    segments, info = model.transcribe(audio, )
    language = info[0]
    print("Transcription language", info[0])
    segments = list(segments)
    for segment in segments:
        # print(segment)
        print("[%.2fs -> %.2fs] %s" %
              (segment.start, segment.end, segment.text))
    return language, segments

def format_time(seconds):

    hours = math.floor(seconds / 3600)
    seconds %= 3600
    minutes = math.floor(seconds / 60)
    seconds %= 60
    milliseconds = round((seconds - math.floor(seconds)) * 1000)
    seconds = math.floor(seconds)
    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:01d},{milliseconds:03d}"

    return formatted_time

def generate_subtitle_file(input_video_name, language, segments):
    subtitle_file_name = input_video_name.rsplit('.', 1)[0]

    subtitle_file = f"{subtitle_file_name}.{language}.srt"
    text = ""
    for index, segment in enumerate(segments):
        segment_start = format_time(segment.start)
        segment_end = format_time(segment.end)
        text += f"{str(index+1)} \n"
        text += f"{segment_start} --> {segment_end} \n"
        text += f"{segment.text} \n"
        text += "\n"

    f = open(subtitle_file, "w")
    f.write(text)
    f.close()

    return subtitle_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    #Empty the uploads folder
    files = os.listdir(UPLOAD_FOLDER)
    for file in files:
        os.remove(os.path.join(UPLOAD_FOLDER, file))

    if 'videoFile' not in request.files:
        return 'No file part'
    file = request.files['videoFile']
    
    if file.filename == '':
        return 'No selected file'
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        extracted_audio = extract_audio(filepath)

        # Run Whisper transcription
        language, segments = transcribe(extracted_audio)

        # Convert transcription result to SRT
        srt_filepath = generate_subtitle_file(filepath, language, segments)

        # Return the SRT file for download
        return jsonify({"status": "success", "srt_url": srt_filepath})

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
