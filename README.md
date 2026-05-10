# ECG Personal Photo Lock

ECG Personal Photo Lock is a desktop authentication prototype that identifies one of five subjects from ECG heartbeat segments, then unlocks and displays that subject's photo when the classification confidence passes an 80% majority-vote threshold.

The project was built for the HCI ECG-based authentication assignment. It uses the PTB Diagnostic ECG Database, ECG preprocessing, Daubechies wavelet features, and three machine-learning classifiers with parameter comparison.

## Features

- Tkinter desktop interface with Training, Results, ECG Viewer, Subject Manager, and Lock Screen tabs.
- PTB Diagnostic ECG Database loader using WFDB records.
- Five-subject identification workflow.
- ECG preprocessing pipeline:
  - baseline wander removal
  - Butterworth bandpass filtering
  - 50 Hz notch filtering
  - R-peak detection
  - heartbeat segmentation
- Wavelet feature extraction using `db1`, `db2`, and `db4`.
- Classifier comparison across:
  - Support Vector Machine
  - K-Nearest Neighbors
  - Random Forest
- Parameter search for each classifier.
- Majority-vote identification rule: a subject is accepted only when at least 80% of ECG segments vote for the same known subject.
- Photo unlock interface that displays the authenticated subject's image.
- ECG viewer for raw and filtered ECG visualization with detected R-peaks.

## Project Structure

```text
ecg_photo_lock/
+-- data/
|   +-- dataset_loader.py        # PTBDB loading, segmentation, feature dataset creation
+-- gui/
|   +-- app.py                   # Main Tkinter application
|   +-- training_tab.py          # Dataset selection and training workflow
|   +-- results_tab.py           # Classifier and wavelet comparison table
|   +-- lock_tab.py              # Authentication / photo lock screen
|   +-- ecg_viewer_tab.py        # Raw and filtered ECG plots
|   +-- subject_tab.py           # Photo assignment for each subject
+-- ml/
|   +-- ecg_preprocessing.py     # ECG filtering, R-peak detection, segmentation
|   +-- feature_extraction.py    # Wavelet features
|   +-- classifiers.py           # SVM, KNN, Random Forest wrappers
|   +-- training_engine.py       # Training and comparison orchestration
+-- scripts/
|   +-- export_ptb_csv.py        # Export PTB WFDB records to CSV for lock-screen tests
+-- main.py
+-- requirements.txt
+-- README.md
```

## Requirements

- Python 3.10 to 3.13 is recommended.
- Avoid Python 3.14 for this project because some scientific packages may not provide stable prebuilt Windows wheels yet.

Install dependencies:

```bash
pip install -r requirements.txt
```

Required Python packages:

```text
numpy
scipy
PyWavelets
scikit-learn
matplotlib
Pillow
wfdb
```

## Dataset

The app is designed for the PTB Diagnostic ECG Database:

[PTB Diagnostic ECG Database v1.0.0](https://physionet.org/physiobank/database/ptbdb/)

Expected local folder layout:

```text
physionet.org/
+-- files/
    +-- ptbdb/
        +-- 1.0.0/
            +-- patient001/
            |   +-- s0010_re.hea
            |   +-- s0010_re.dat
            |   +-- ...
            +-- patient002/
            +-- ...
```

When training, select the dataset root folder:

```text
D:\FCIS-2024\FCIS-4th-Year\8th Term\HCI\Project\physionet.org\files\ptbdb\1.0.0
```

## Running the App

```bash
python main.py
```

Typical workflow:

1. Open the Training tab.
2. Select the PTBDB `1.0.0` folder.
3. Keep subjects set to `5`.
4. Press Start Training.
5. Review the classifier and wavelet comparison in the Results tab.
6. Assign one photo per subject in the Subjects tab.
7. Use the Lock Screen tab to scan a demo signal or load an ECG CSV file.

## CSV ECG Signals for Lock Screen Testing

The PTB database you downloaded is not stored as CSV. It is stored in WFDB format using `.hea` and `.dat` files. The app can train directly from those files.

For the Lock Screen file input, the app accepts a `.csv` or `.npy` file containing a raw ECG signal. The simplest option is to export one lead from your existing PTB records.

Example:

```bash
python scripts/export_ptb_csv.py ^
  --root "D:\FCIS-2024\FCIS-4th-Year\8th Term\HCI\Project\physionet.org\files\ptbdb\1.0.0" ^
  --patient patient001 ^
  --record s0010_re ^
  --lead 1 ^
  --output samples\patient001_s0010_lead2.csv
```

Then in the Lock Screen:

1. Select `Load ECG file (.npy / .csv)`.
2. Browse to `samples\patient001_s0010_lead2.csv`.
3. Press Scan ECG.

Other ECG sources:

- [MIT-BIH Arrhythmia Database](https://www.physionet.org/content/mitdb/1.0.0/) from PhysioNet, also WFDB format.
- [ECG Heartbeat Categorization Dataset](https://www.kaggle.com/datasets/shayanfazeli/heartbeat), which provides preprocessed heartbeat CSV files derived from MIT-BIH and PTB.

For this project, PTB records exported with `scripts/export_ptb_csv.py` are the best match because they come from the same subject identity dataset used during training.

The Lock Screen also reads the `patient###` token from exported PTB CSV filenames. If a file such as `patient001_s0010_lead2.csv` is scanned while the model was trained on `patient068, patient078, patient100, patient120, patient140`, the app rejects it as `Unidentified` before displaying any subject photo.

## Methodology

### 1. Data Preparation

The system selects five PTB patient folders and reads ECG records using the WFDB package. Each ECG record is converted into heartbeat segments after preprocessing. The generated feature rows are split into training and testing sets using a stratified split.

### 2. Preprocessing

The preprocessing pipeline removes common ECG noise before feature extraction:

```text
Raw ECG
  |
  v
Baseline wander removal
  |
  v
Bandpass filtering
  |
  v
Powerline notch filtering
  |
  v
R-peak detection
  |
  v
Heartbeat segmentation
```

### 3. Feature Extraction

Each heartbeat segment is decomposed with a Discrete Wavelet Transform. The project compares three Daubechies mother wavelets:

- `db1`
- `db2`
- `db4`

For each wavelet sub-band, statistical features are extracted:

- mean
- standard deviation
- energy
- maximum absolute value
- minimum absolute value

### 4. Classification

The system trains and compares three classifiers:

| Classifier | Parameters Tested |
|---|---|
| SVM | kernel, C, gamma |
| KNN | number of neighbors, distance metric |
| Random Forest | number of trees, maximum depth |

The Results tab reports training accuracy, testing accuracy, selected wavelet, and parameters for each experiment.

### 5. Identification Rule

The trained classifier predicts a subject label for each heartbeat segment. The final identity is accepted only if more than 80% of the segments vote for the same subject.

For exported PTB CSV files, the app also checks whether the filename patient ID belongs to the trained subject list. A patient outside the training list is treated as an unknown person and rejected as `Unidentified`.

```text
ECG signal
  |
  v
Heartbeat predictions
  |
  v
Majority vote
  |
  v
Confidence >= 80% ?
  +-- Yes: show subject photo
  +-- No: unidentified
```

## Notes

- `pywt` is imported from the `PyWavelets` package.
- If `ModuleNotFoundError: No module named 'pywt'` appears, install requirements into the same Python interpreter used by your IDE.
- If training is slow, reduce `MAX_RECORDS_PER_PATIENT` in `data/dataset_loader.py`.
- Lead index `1` is used by default because it corresponds to Lead II in the PTB record layout.

