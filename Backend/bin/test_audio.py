#!/usr/bin/env python3
"""
Test audio playback functionality
Tests playing the voice_welcome.mp3 file using different audio libraries
"""

import os
import sys
import time

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_with_pygame():
    """Test audio playback using pygame"""
    try:
        import pygame
        print("Testing with pygame...")
        
        pygame.mixer.init()
        audio_file = os.path.join(project_root, "assets", "sounds", "voice_welcome.mp3")
        
        if os.path.exists(audio_file):
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            print("✓ Pygame playback successful")
            return True
        else:
            print(f"✗ Audio file not found: {audio_file}")
            return False
            
    except ImportError:
        print("✗ Pygame not installed")
        return False
    except Exception as e:
        print(f"✗ Pygame error: {e}")
        return False
    finally:
        try:
            pygame.mixer.quit()
        except:
            pass

def test_with_pygame_mixer():
    """Test audio playback using pygame.mixer directly"""
    try:
        import pygame.mixer
        print("Testing with pygame.mixer...")
        
        pygame.mixer.init()
        audio_file = os.path.join(project_root, "assets", "sounds", "voice_welcome.mp3")
        
        if os.path.exists(audio_file):
            sound = pygame.mixer.Sound(audio_file)
            sound.play()
            
            # Wait for playback to complete
            time.sleep(sound.get_length() + 0.5)
            
            print("✓ Pygame.mixer playback successful")
            return True
        else:
            print(f"✗ Audio file not found: {audio_file}")
            return False
            
    except ImportError:
        print("✗ Pygame.mixer not available")
        return False
    except Exception as e:
        print(f"✗ Pygame.mixer error: {e}")
        return False
    finally:
        try:
            pygame.mixer.quit()
        except:
            pass

def test_with_playsound():
    """Test audio playback using playsound"""
    try:
        from playsound import playsound
        print("Testing with playsound...")
        
        audio_file = os.path.join(project_root, "assets", "sounds", "voice_welcome.mp3")
        
        if os.path.exists(audio_file):
            playsound(audio_file)
            print("✓ Playsound playback successful")
            return True
        else:
            print(f"✗ Audio file not found: {audio_file}")
            return False
            
    except ImportError:
        print("✗ Playsound not installed")
        return False
    except Exception as e:
        print(f"✗ Playsound error: {e}")
        return False

def test_with_simpleaudio():
    """Test audio playback using simpleaudio"""
    try:
        import simpleaudio as sa
        print("Testing with simpleaudio...")
        
        audio_file = os.path.join(project_root, "assets", "sounds", "voice_welcome.mp3")
        
        if os.path.exists(audio_file):
            wave_obj = sa.WaveObject.from_wave_file(audio_file)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            
            print("✓ Simpleaudio playback successful")
            return True
        else:
            print(f"✗ Audio file not found: {audio_file}")
            return False
            
    except ImportError:
        print("✗ Simpleaudio not installed")
        return False
    except Exception as e:
        print(f"✗ Simpleaudio error: {e}")
        return False

def test_with_ffpyplayer():
    """Test audio playback using ffpyplayer (Kivy compatible)"""
    try:
        from ffpyplayer.player import MediaPlayer
        print("Testing with ffpyplayer...")
        
        audio_file = os.path.join(project_root, "assets", "sounds", "voice_welcome.mp3")
        
        if os.path.exists(audio_file):
            player = MediaPlayer(audio_file)
            
            while not player.get_eof():
                time.sleep(0.1)
            
            print("✓ FFpyplayer playback successful")
            return True
        else:
            print(f"✗ Audio file not found: {audio_file}")
            return False
            
    except ImportError:
        print("✗ FFpyplayer not installed")
        return False
    except Exception as e:
        print(f"✗ FFpyplayer error: {e}")
        return False

def check_audio_file():
    """Check if the audio file exists and get its info"""
    audio_file = os.path.join(project_root, "assets", "sounds", "voice_welcome.mp3")
    
    print(f"Checking audio file: {audio_file}")
    
    if os.path.exists(audio_file):
        size = os.path.getsize(audio_file)
        print(f"✓ Audio file exists ({size} bytes)")
        
        # Try to get basic info
        try:
            import mutagen
            audio = mutagen.File(audio_file)
            if audio:
                print(f"  Duration: {audio.info.length:.2f} seconds")
                print(f"  Bitrate: {audio.info.bitrate} bps")
                print(f"  Format: {audio.info.mime[0] if audio.info.mime else 'Unknown'}")
        except ImportError:
            print("  Install mutagen for detailed audio info")
        except Exception as e:
            print(f"  Error reading audio info: {e}")
        
        return True
    else:
        print(f"✗ Audio file not found: {audio_file}")
        return False

def main():
    """Run all audio tests"""
    print("=" * 50)
    print("Audio Playback Test Suite")
    print("=" * 50)
    
    # Check audio file first
    if not check_audio_file():
        print("\nAudio file not found. Please ensure voice_welcome.mp3 exists in assets/sounds/")
        return
    
    print("\n" + "-" * 30)
    print("Testing different audio libraries...")
    print("-" * 30)
    
    results = []
    
    # Test different libraries
    results.append(("pygame", test_with_pygame()))
    results.append(("pygame.mixer", test_with_pygame_mixer()))
    results.append(("playsound", test_with_playsound()))
    results.append(("simpleaudio", test_with_simpleaudio()))
    results.append(("ffpyplayer", test_with_ffpyplayer()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    
    for library, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{library:15} : {status}")
    
    # Recommendations
    working_libs = [lib for lib, success in results if success]
    
    if working_libs:
        print(f"\n✓ Working libraries: {', '.join(working_libs)}")
        print("Recommendation: Use pygame.mixer for Kivy compatibility")
    else:
        print("\n✗ No audio libraries working")
        print("Install one of the following:")
        print("  pip install pygame")
        print("  pip install playsound")
        print("  pip install simpleaudio")
        print("  pip install ffpyplayer")

if __name__ == "__main__":
    main()
