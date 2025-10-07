# SmartTurn-Simulation (Demo)

A simple **Streamlit** demo that simulates a hospital bed performing scheduled position changes
to help prevent pressure injuries. It includes:
- Protocol scheduler (e.g., every 120 minutes, alternate right/left at a given angle)
- Manual override controls
- Event log with timestamps, angle, side, and mode (AUTO/MANUAL)
- Late change alerts when the protocol isn't followed on time
- CSV export of the log

## Install
```bash
git clone https://github.com/USERNAME/SmartTurn-Simulation.git
cd SmartTurn-Simulation
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Notes
- This is a simulation only (no real hardware).
- Time is simulated. Use the **Advance Time** buttons to move the clock forward for demo purposes.
