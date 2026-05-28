"""Pygame mixer-backed audio manager."""

from pathlib import Path
import time

import pygame

from config import Config


class AudioManager:
    """Own game music, short SFX, and speed-reactive engine hum."""

    MUSIC_TRACKS = [
        {
            "name": "8-bit Space Theme",
            "filename": "8-bit_space_theme.wav",
        },
        {
            "name": "8-bit Epic Space Shooter",
            "filename": "8bit_epic_space_shooter.mp3",
        },
    ]

    SFX_FILES = {
        "menu_select": "menu_select.wav",
        "menu_start": "menu_start.wav",
        "star_pickup": "star_pickup.wav",
        "boost": "boost.wav",
        "asteroid_bounce": "asteroid_bounce.wav",
        "mine_explosion": "mine_explosion.wav",
        "round_win": "round_win.wav",
        "return_to_menu": "return_to_menu.wav",
    }

    def __init__(self):
        self.enabled = bool(Config.AUDIO_ENABLED)
        self.muted_music = False
        self.muted_sfx = False
        self.base_dir = Path(__file__).resolve().parents[1]
        self.sfx_dir = self.base_dir / "assets" / "audio" / "sfx"
        self.music_dir = self.base_dir / "assets" / "audio" / "music"
        self.music_track_index = 0
        self.sounds = {}
        self.engine_sounds = []
        self.engine_channels = []
        self.engine_channel_index = 0
        self.engine_bucket = None
        self.engine_started = False
        self.last_engine_switch_time = 0.0

        if not self.enabled:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(2)
            self.engine_channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self._load_sounds()
        except pygame.error as exc:
            print(f"Audio disabled: {exc}")
            self.enabled = False

    def _load_sounds(self):
        for name, filename in self.SFX_FILES.items():
            path = self.sfx_dir / filename
            if path.exists():
                self.sounds[name] = pygame.mixer.Sound(str(path))
                self.sounds[name].set_volume(Config.SFX_VOLUME)

        self.engine_sounds = []
        for index in range(Config.ENGINE_SPEED_BUCKETS):
            path = self.sfx_dir / f"engine_{index:02d}.wav"
            if path.exists():
                sound = pygame.mixer.Sound(str(path))
                sound.set_volume(Config.ENGINE_VOLUME)
                self.engine_sounds.append(sound)

    def set_music_volume(self, volume):
        Config.MUSIC_VOLUME = max(0.0, min(1.0, volume))
        if self.enabled:
            pygame.mixer.music.set_volume(Config.MUSIC_VOLUME)

    def set_sfx_volume(self, volume):
        Config.SFX_VOLUME = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(Config.SFX_VOLUME)

    def set_engine_volume(self, volume):
        Config.ENGINE_VOLUME = max(0.0, min(1.0, volume))
        for sound in self.engine_sounds:
            sound.set_volume(Config.ENGINE_VOLUME)

    def current_music_track(self):
        return self.MUSIC_TRACKS[self.music_track_index]

    def current_music_name(self):
        return self.current_music_track()["name"]

    def current_music_path(self):
        return self.music_dir / self.current_music_track()["filename"]

    def play_music(self):
        music_path = self.current_music_path()
        if not self.enabled or self.muted_music or not music_path.exists():
            return
        try:
            if pygame.mixer.music.get_busy():
                return
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(Config.MUSIC_VOLUME)
            pygame.mixer.music.play(loops=-1)
        except pygame.error as exc:
            print(f"Music unavailable: {exc}")

    def switch_music_track(self, direction=1):
        if not self.enabled:
            return None
        was_playing = pygame.mixer.music.get_busy() and not self.muted_music
        self.music_track_index = (self.music_track_index + direction) % len(self.MUSIC_TRACKS)
        pygame.mixer.music.stop()
        if was_playing:
            self.play_music()
        return self.current_music_name()

    def stop_music(self):
        if self.enabled:
            pygame.mixer.music.stop()

    def play(self, name):
        if not self.enabled or self.muted_sfx:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.set_volume(Config.SFX_VOLUME)
            sound.play()

    def update_engine(self, game_state):
        if not self.enabled or self.muted_sfx or not self.engine_sounds or not self.engine_channels:
            self.stop_engine()
            return

        max_speed = 0.0
        for ship in game_state.ships.values():
            if ship.alive and not game_state.game_over:
                max_speed = max(max_speed, ship.velocity.length())

        speed_scale = max(0.0, min(1.0, max_speed / Config.MAX_SPEED))
        if speed_scale < 0.03:
            self.stop_engine()
            return

        bucket = min(len(self.engine_sounds) - 1, int(speed_scale * len(self.engine_sounds)))
        volume = Config.ENGINE_VOLUME * (0.35 + 0.65 * speed_scale)

        active_channel = self.engine_channels[self.engine_channel_index]
        now = time.monotonic()
        can_switch = now - self.last_engine_switch_time >= Config.ENGINE_MIN_SWITCH_INTERVAL
        if bucket != self.engine_bucket and (can_switch or not active_channel.get_busy()):
            next_index = 1 - self.engine_channel_index
            next_channel = self.engine_channels[next_index]
            next_channel.set_volume(volume)
            next_channel.play(
                self.engine_sounds[bucket],
                loops=-1,
                fade_ms=Config.ENGINE_CROSSFADE_MS
            )
            active_channel.fadeout(Config.ENGINE_CROSSFADE_MS)
            self.engine_channel_index = next_index
            self.engine_bucket = bucket
            self.engine_started = True
            self.last_engine_switch_time = now
        self.engine_channels[self.engine_channel_index].set_volume(volume)

    def stop_engine(self):
        if self.engine_channels and self.engine_started:
            for channel in self.engine_channels:
                channel.fadeout(120)
        self.engine_bucket = None
        self.engine_started = False

    def toggle_music(self):
        if not self.enabled:
            return
        self.muted_music = not self.muted_music
        if self.muted_music:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
            self.play_music()

    def toggle_sfx(self):
        if not self.enabled:
            return
        self.muted_sfx = not self.muted_sfx
        if self.muted_sfx:
            self.stop_engine()

    def close(self):
        if not self.enabled:
            return
        self.stop_engine()
        pygame.mixer.music.stop()
