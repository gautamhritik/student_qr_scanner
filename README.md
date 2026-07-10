# Mining Vehicle QR Scanner

This project scans QR codes mounted on moving mining vehicles and trucks from a
pole or gate camera. Each QR payload contains vehicle, driver, cargo, route, and
permit information, and every accepted scan updates a local JSON database with
real-time in/out vehicle status.

Maintainer: Hritik Gautam <gautamhritik@gmail.com>

## Setup

```powershell
cd <project-folder>
python -m pip install -r requirements.txt
```

## Tests

```powershell
python -m pytest
```

## Fleet Registry

The mining QR registry is stored in `data/fleet.json`. Records include vehicle,
driver, cargo, route, site, gate, checkpoint, permit, and optional RFID data.

Useful commands:

```powershell
python manage_fleet.py list
python manage_fleet.py add --vehicle-id TRUCK-100 --plate-number MH12AB1000 --vehicle-type dump_truck --driver-id DRV-100 --driver-name "Amit Sharma" --license-number MH-DRV-100 --material-type iron_ore --load-status loaded --source-zone pit-a --destination-zone crusher-1 --route-id route-pit-a-crusher-1 --site-id mine-1 --gate-id main-gate --checkpoint-id gate-1
python manage_fleet.py remove --vehicle-id TRUCK-100
```

## Gate And Camera Registry

Pole-camera assignments are stored in `data/gates.json`. The scanner validates
`site_id`, `gate_id`, `checkpoint_id`, `camera_id`, and `direction` against this
registry before opening the camera.

Useful commands:

```powershell
python manage_gates.py list
python manage_gates.py add --site-id mine-1 --gate-id north-gate --checkpoint-id gate-3 --camera-id pole-cam-3 --allowed-directions in,out --location "north haul road"
python manage_gates.py remove --site-id mine-1 --gate-id north-gate --checkpoint-id gate-3 --camera-id pole-cam-3
```

## Generate Mining Vehicle QR Codes

```powershell
python generate_vehicle_qrs.py
python generate_vehicle_qrs.py --valid-days 180
python generate_vehicle_qrs.py --no-expiry
```

The generator creates:

- `mining_vehicle_qrs/`
- `mining_vehicle_qrs_large_print/`
- `data/fleet.csv`

Use the large-print QR files for pole-camera and distance testing.

Generated QR payloads include `payload_version`, `payload_id`, `issued_at`,
optional `expires_on`, and a checksum. The scanner validates these fields so a
modified or expired QR payload is stored as a validation failure instead of a
trusted movement event.

Inspect a QR image or raw payload:

```powershell
python inspect_qr_payload.py --image mining_vehicle_qrs\02_truck-002.png
python inspect_qr_payload.py --payload-file payload.txt --json
```

## Run A Gate Scanner

Use camera `0` for the default laptop camera. IP camera or phone camera streams
can be passed as URLs.

```powershell
python scan_camera.py --camera 0 --site-id mine-1 --gate-id main-gate --checkpoint-id gate-1 --camera-id pole-cam-1 --direction in
python scan_camera.py --camera 0 --site-id mine-1 --gate-id main-gate --checkpoint-id gate-1 --camera-id pole-cam-1 --direction out
python scan_camera.py
```

Useful options:

```powershell
python scan_camera.py --camera 0 --backend dshow --direction in
python scan_camera.py --camera "http://PHONE_IP:8080/video" --direction in
python scan_camera.py --direction in --width 3840 --height 2160 --digital-zoom 2
python scan_camera.py --direction in --vote-window 5 --min-votes 3
python scan_camera.py --direction in --save-scans
python scan_camera.py --direction in --no-preview
python scan_camera.py --direction in --max-scans 10
python scan_camera.py --direction in --skip-gate-validation
```

If the scanner says OpenCV preview is unavailable, QR scanning still continues in
terminal-only mode. Check the installed OpenCV build with:

```powershell
python check_opencv.py
```

If `opencv-python-headless` is installed, remove it and reinstall the GUI-enabled
package:

```powershell
python -m pip uninstall opencv-python-headless -y
python -m pip install --upgrade --force-reinstall opencv-python
```

The scanner uses majority voting by default so a single noisy frame does not
create a movement event. Duplicate scans for the same vehicle, checkpoint, and
direction within the cooldown period are stored as `duplicate_suppressed` and do
not update real-time vehicle state.

## Mining Database

Operational data is stored in `mining_database/` by default:

- `mining_database/events.json`
- `mining_database/records/*.json`
- `mining_database/vehicle_state.json`

Accepted `in` scans mark a vehicle as `inside`. Accepted `out` scans mark a
vehicle as `outside`. Validation failures and duplicate-suppressed events remain
in event history for reporting.

## Export Mining Reports

```powershell
python export_mining_scans.py
python export_mining_scans.py --date-from 2026-07-01 --date-to 2026-07-31
python export_mining_scans.py --gate-id main-gate --direction in
python export_mining_scans.py --vehicle-id TRUCK-001
python export_mining_scans.py --driver-id DRV-001
python export_mining_scans.py --material-type iron_ore
```

The exporter creates:

- `exports/mining_events.csv`
- `exports/mining_summary.json`
- `exports/mining_report.html`
- `exports/vehicle_state.csv`
- `exports/vehicle_state.json`

Reports summarize current inside/outside status, vehicle movement, drivers,
routes, materials, gates, cameras, duplicate-suppressed scans, validation
failures, and ANPR placeholder match status.

## Export Trip Reports

Use `export_trips.py` to reconstruct vehicle trips by pairing accepted `in` and
`out` scan events. It calculates trip duration, completed tonnage, open trips,
missing exits, and orphan exits.

```powershell
python export_trips.py
python export_trips.py --trip-status completed
python export_trips.py --material-type iron_ore
python export_trips.py --route-id route-pit-a-crusher-1
```

The trip exporter creates:

- `exports/mining_trips.csv`
- `exports/mining_trips_summary.json`
- `exports/mining_trips_report.html`

## Current Vehicle Status

Use `vehicle_status.py` for a quick terminal view of the current inside/outside
state without opening JSON files.

```powershell
python vehicle_status.py
python vehicle_status.py --status inside
python vehicle_status.py --gate-id main-gate
python vehicle_status.py --material-type iron_ore --json
python vehicle_status.py --csv-output exports\vehicle_state_now.csv
```

## Scan Saved Images

Use `scan_images.py` to process camera snapshots, test images, or a folder of
field captures without opening a live camera.

```powershell
python scan_images.py captures\ --direction in --site-id mine-1 --gate-id main-gate --checkpoint-id gate-1 --camera-id pole-cam-1
python scan_images.py captures\failed_frame.jpg --direction out --save-failures
python scan_images.py captures\
```

Saved-image scans write into the same `mining_database/` event history and update
`vehicle_state.json` for accepted movement events.

## Movement Audit

Use `event_audit.py` to find operational anomalies in event history:

```powershell
python event_audit.py
python event_audit.py --stale-inside-hours 8
python event_audit.py --rebuild-state
```

The audit creates:

- `exports/movement_audit.json`
- `exports/movement_audit.csv`
- `exports/movement_audit.html`

It flags validation failures, duplicate-suppressed scans, repeated accepted
directions, vehicles scanned out without a prior accepted in movement, and
vehicles still marked inside beyond the selected hour threshold.

## Rugged-Condition Benchmark

Use the benchmark tool to test QR decoding under synthetic mining conditions:
dust, blur, glare, low light, crop, rotation, and distance scaling.

```powershell
python generate_vehicle_qrs.py
python benchmark_qr_conditions.py --input-dir mining_vehicle_qrs --output-dir exports\qr_condition_benchmark
```

The benchmark creates CSV, JSON, HTML, and generated condition images in the
selected output folder.

## Detection Notes

The scanner uses OpenCV's QR detector and retries decoding on enhanced frame
variants: center crops, grayscale, contrast normalization, gamma correction,
thresholding, sharpening, and upscaled versions of the camera frame. Long-distance
pole-camera scanning still depends on camera resolution, focus, QR print size,
vehicle speed, lighting, and placement angle.

ANPR is prepared as a future verification layer. The schema stores
`plate_number`, `anpr_plate_number`, and `anpr_match_status`, but full ANPR is
not implemented yet.
