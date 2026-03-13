import os
import sys
import pytest
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

class TestStep1ExtractFrames:
    """Unit tests for step1_extract_frames.py"""
    
    def test_extract_frames_creates_manifest(self):
        """Test that extract_frames creates a manifest.json file"""
        pytest.importorskip("cv2")
        
        from steps.step1_extract_frames import extract_frames
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = "samples/me.mp3"
            if not os.path.exists(video_path):
                pytest.skip("Sample video not found")
            
            import cv2
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                pytest.skip("Sample is not a valid video file")
            cap.release()
            
            manifest = extract_frames(video_path, 1.0, tmpdir)
            assert os.path.exists(manifest)
            
            with open(manifest) as f:
                data = json.load(f)
            assert isinstance(data, list)

    def test_extract_frames_output_dir_created(self):
        """Test that output directory is created if it doesn't exist"""
        pytest.importorskip("cv2")
        
        from steps.step1_extract_frames import extract_frames
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "new_dir")
            video_path = "samples/me.mp3"
            if not os.path.exists(video_path):
                pytest.skip("Sample video not found")
            
            import cv2
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                pytest.skip("Sample is not a valid video file")
            cap.release()
            
            extract_frames(video_path, 1.0, output_dir)
            assert os.path.isdir(output_dir)


class TestStep3TranscribeOriginal:
    """Unit tests for step3_transcribe_original.py"""
    
    def test_format_timestamp(self):
        """Test timestamp formatting"""
        pytest.importorskip("faster_whisper")
        
        from steps.step3_transcribe_original import _format_ts
        
        assert _format_ts(0) == "00:00:00"
        assert _format_ts(65) == "00:01:05"
        assert _format_ts(3665) == "01:01:05"


class TestStep4LLMScript:
    """Unit tests for step4_llm_script.py"""
    
    def test_llm_script_imports(self):
        """Test that step4_llm_script can be imported"""
        pytest.importorskip("ollama")
        
        import steps.step4_llm_script
        assert hasattr(steps.step4_llm_script, 'generate_script')


class TestConfig:
    """Tests for configuration"""
    
    def test_config_imports(self):
        """Test that config can be imported"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        import config
        assert hasattr(config, 'OLLAMA_URL')
        assert hasattr(config, 'FRAME_INTERVAL')
        assert hasattr(config, 'VISION_MODEL')
    
    def test_venv_paths_exist(self):
        """Test that configured venv paths exist"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        import config
        
        assert os.path.isfile(config.CHATTERBOX_PYTHON)
        assert os.path.isfile(config.FASTER_WHISPER_PYTHON)
        assert os.path.isfile(config.UPLOADER_PYTHON)
    
    def test_tts_settings_valid(self):
        """Test that TTS settings are valid numbers"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        import config
        
        assert 0 <= config.TTS_EXAGGERATION <= 1
        assert 0 < config.TTS_TEMPERATURE < 1
        assert 0 <= config.TTS_CFG_WEIGHT <= 1
    
    def test_whisper_settings_valid(self):
        """Test that Whisper settings are valid"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        import config
        
        assert config.WHISPER_MODEL in ["tiny", "base", "small", "medium", "large-v3"]
        assert config.WHISPER_BEAM_SIZE > 0


class TestPipeline:
    """Tests for pipeline.py"""
    
    def test_get_video_duration(self):
        """Test video duration extraction"""
        from pipeline import get_video_duration
        
        if not os.path.exists("samples/me.mp3"):
            pytest.skip("Sample not found")
        
        duration = get_video_duration("samples/me.mp3")
        assert duration >= 0


class TestUtils:
    """Utility function tests"""
    
    def test_manifest_json_valid(self):
        """Test that manifest JSON structure is valid"""
        manifest = {
            "test": [
                {"path": "frame_00001.png", "timestamp": "00:00:01"},
                {"path": "frame_00002.png", "timestamp": "00:00:02"},
            ]
        }
        
        json_str = json.dumps(manifest)
        parsed = json.loads(json_str)
        assert len(parsed["test"]) == 2
        assert parsed["test"][0]["path"] == "frame_00001.png"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
