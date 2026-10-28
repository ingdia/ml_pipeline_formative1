# ml_pipeline_formative1

## Task 1: Exploratory analysis and forecasting model

**Owner:** Anglebert Shumbusho Ishimwe

**Dataset:** Air Quality, UCI Machine Learning Repository (Kaggle copy). Hourly readings from 10/03/2004 to 04/04/2005, 9,357 records. Licence CC BY 4.0, DOI [10.24432/C59K5F](https://doi.org/10.24432/C59K5F).

### Files

| File | Purpose |
|---|---|
| `notebooks/data/AirQualityUCI.csv` | Raw dataset |
| `src/preprocessing.py` | Loading, cleaning and feature building, shared with Task 4 |
| `notebooks/task1_eda_and_model.ipynb` | Exploration, six analytical questions, model training and results |
| `notebooks/models/co_forecast_model.joblib` | Trained forecasting model (created by the notebook) |
| `notebooks/models/model_config.json` | Model and preprocessing settings (created by the notebook) |
| `notebooks/figures/` | Analysis figures (created by the notebook) |
| `requirements.txt` | Python packages |

### How to run

Run these steps in order from the repository root.

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```
2. Activate it:
   ```bash
   source .venv/bin/activate        # macOS and Linux
   .venv\Scripts\activate           # Windows
   ```
3. Install the packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Open `notebooks/task1_eda_and_model.ipynb` in VS Code and select the `.venv` Python interpreter as the kernel.
5. Click **Run All**. The notebook reads `data/AirQualityUCI.csv` from the `notebooks/` folder and saves the model to `notebooks/models/` and the figures to `notebooks/figures/`. Part C tunes several models, so it takes a few minutes.

### Results

All findings, the experiment table and the final model's test scores can be seen in the notebook outputs.
