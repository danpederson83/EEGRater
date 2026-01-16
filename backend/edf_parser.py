"""
EDF file parser for extracting 10-second EEG snippets.
No external dependencies except numpy - parses EDF format directly.
"""
import os
import json
import hashlib
import struct
import numpy as np
from pathlib import Path
from typing import Optional


def read_edf(filepath):
    """
    Read an EDF file and return the data and metadata.

    Returns:
        dict with keys: channel_names, data (in microvolts), sampling_rate, duration
    """
    with open(filepath, 'rb') as f:
        # === READ HEADER ===
        # Version (8 bytes)
        version = f.read(8).decode('ascii').strip()

        # Patient ID (80 bytes)
        patient_id = f.read(80).decode('ascii').strip()

        # Recording ID (80 bytes)
        recording_id = f.read(80).decode('ascii').strip()

        # Start date (8 bytes)
        start_date = f.read(8).decode('ascii').strip()

        # Start time (8 bytes)
        start_time = f.read(8).decode('ascii').strip()

        # Header size (8 bytes)
        header_size = int(f.read(8).decode('ascii').strip())

        # Reserved (44 bytes)
        reserved = f.read(44).decode('ascii').strip()

        # Number of data records (8 bytes)
        n_records = int(f.read(8).decode('ascii').strip())

        # Duration of data record (8 bytes)
        record_duration = float(f.read(8).decode('ascii').strip())

        # Number of signals/channels (4 bytes)
        n_channels = int(f.read(4).decode('ascii').strip())

        # === READ CHANNEL HEADERS ===
        # Labels (16 bytes each)
        channel_names = []
        for _ in range(n_channels):
            channel_names.append(f.read(16).decode('ascii').strip())

        # Transducer type (80 bytes each) - skip
        for _ in range(n_channels):
            f.read(80)

        # Physical dimension (8 bytes each) - skip
        for _ in range(n_channels):
            f.read(8)

        # Physical minimum (8 bytes each)
        physical_min = []
        for _ in range(n_channels):
            physical_min.append(float(f.read(8).decode('ascii').strip()))

        # Physical maximum (8 bytes each)
        physical_max = []
        for _ in range(n_channels):
            physical_max.append(float(f.read(8).decode('ascii').strip()))

        # Digital minimum (8 bytes each)
        digital_min = []
        for _ in range(n_channels):
            digital_min.append(int(f.read(8).decode('ascii').strip()))

        # Digital maximum (8 bytes each)
        digital_max = []
        for _ in range(n_channels):
            digital_max.append(int(f.read(8).decode('ascii').strip()))

        # Prefiltering (80 bytes each) - skip
        for _ in range(n_channels):
            f.read(80)

        # Number of samples per data record (8 bytes each)
        samples_per_record = []
        for _ in range(n_channels):
            samples_per_record.append(int(f.read(8).decode('ascii').strip()))

        # Reserved (32 bytes each) - skip
        for _ in range(n_channels):
            f.read(32)

        # === READ DATA ===
        # Seek to data start (should already be there, but make sure)
        f.seek(header_size)

        # Calculate total samples per channel
        total_samples = n_records * samples_per_record[0]  # Assuming all channels same

        # Initialize data array
        data = np.zeros((n_channels, total_samples))

        # Read data records
        for rec in range(n_records):
            for ch in range(n_channels):
                n_samples = samples_per_record[ch]
                # Read as 16-bit signed integers
                raw_data = f.read(n_samples * 2)
                digital_values = np.frombuffer(raw_data, dtype=np.int16)

                # Convert to physical values (microvolts)
                # Must convert to float first to avoid int16 overflow!
                scale = (physical_max[ch] - physical_min[ch]) / (digital_max[ch] - digital_min[ch])
                physical_values = (digital_values.astype(np.float64) - digital_min[ch]) * scale + physical_min[ch]

                # Store in data array
                start_idx = rec * n_samples
                data[ch, start_idx:start_idx + n_samples] = physical_values

        # Calculate sampling rate (samples per second)
        sampling_rate = samples_per_record[0] / record_duration

        # Total duration
        duration = n_records * record_duration

        return {
            'channel_names': channel_names,
            'data': data,
            'sampling_rate': sampling_rate,
            'duration': duration,
            'n_records': n_records,
            'record_duration': record_duration
        }


class EDFParser:
    def __init__(self, edf_directory: str, cache_directory: str):
        self.edf_directory = Path(edf_directory)
        self.cache_directory = Path(cache_directory)
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.snippet_duration = 10  # seconds
        self._snippets_cache: Optional[list] = None

    def _get_cache_path(self, edf_file: Path) -> Path:
        """Generate cache file path for an EDF file."""
        file_hash = hashlib.md5(str(edf_file).encode()).hexdigest()[:8]
        return self.cache_directory / f"{edf_file.stem}_{file_hash}_snippets.json"

    def _extract_snippets_from_edf(self, edf_path: Path) -> list:
        """Extract 10-second snippets from an EDF file."""
        snippets = []

        try:
            # Load EDF file using our custom reader
            edf_data = read_edf(str(edf_path))

            channel_names = edf_data['channel_names']
            data = edf_data['data']
            sfreq = edf_data['sampling_rate']
            duration = edf_data['duration']

            # Calculate number of complete 10-second snippets
            n_snippets = int(duration // self.snippet_duration)

            for i in range(n_snippets):
                start_time = i * self.snippet_duration
                end_time = start_time + self.snippet_duration

                # Extract data for this time window
                start_sample = int(start_time * sfreq)
                end_sample = int(end_time * sfreq)

                snippet_data = data[:, start_sample:end_sample]

                # Convert to list for JSON serialization
                data_list = snippet_data.tolist()

                snippet_id = f"{edf_path.stem}_snippet_{i:04d}"

                snippets.append({
                    "id": snippet_id,
                    "channels": channel_names,
                    "data": data_list,
                    "sampling_rate": sfreq,
                    "duration": self.snippet_duration,
                    "source_file": edf_path.name,
                    "start_time": start_time,
                    "end_time": end_time
                })

            return snippets

        except Exception as e:
            print(f"Error processing {edf_path}: {e}")
            return []

    def process_edf_file(self, edf_path: Path, force_reprocess: bool = False) -> list:
        """Process an EDF file and cache the snippets."""
        cache_path = self._get_cache_path(edf_path)

        # Check if cached version exists
        if cache_path.exists() and not force_reprocess:
            with open(cache_path, 'r') as f:
                return json.load(f)

        # Extract snippets
        snippets = self._extract_snippets_from_edf(edf_path)

        # Cache the results
        if snippets:
            with open(cache_path, 'w') as f:
                json.dump(snippets, f)

        return snippets

    def get_all_snippets(self, force_reprocess: bool = False) -> list:
        """Get all snippets from all EDF files in the directory."""
        if self._snippets_cache is not None and not force_reprocess:
            return self._snippets_cache

        all_snippets = []

        # Find all EDF files (case-insensitive, avoid duplicates on Windows)
        edf_files = list(set(self.edf_directory.glob("*.edf")) | set(self.edf_directory.glob("*.EDF")))

        for edf_file in edf_files:
            snippets = self.process_edf_file(edf_file, force_reprocess)
            all_snippets.extend(snippets)

        self._snippets_cache = all_snippets
        return all_snippets

    def get_snippet_by_id(self, snippet_id: str) -> Optional[dict]:
        """Get a specific snippet by ID."""
        snippets = self.get_all_snippets()
        for snippet in snippets:
            if snippet["id"] == snippet_id:
                return snippet
        return None

    def get_snippet_ids(self) -> list:
        """Get list of all snippet IDs."""
        snippets = self.get_all_snippets()
        return [s["id"] for s in snippets]
