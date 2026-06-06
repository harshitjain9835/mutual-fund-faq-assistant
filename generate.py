name: Daily Data Ingestion

on:
  schedule:
    # Runs at 10:00 AM IST (4:30 AM UTC) every day
    - cron: '30 4 * * *'
  workflow_dispatch: # Allows manual triggering from the GitHub Actions UI

jobs:
  ingest-and-refresh:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip setuptools wheel
          # Automatically clean hidden Windows encoding issues (null bytes & carriage returns)
          tr -d '\000\r' < requirements.txt > clean_requirements.txt
          echo "Sanitized requirements text:"
          cat clean_requirements.txt
          pip install -r clean_requirements.txt
          
      - name: Run Data Refresh Pipeline
        env:
          GROQ_API_KEY: os.environ.get("GROQ_API_KEY", "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"

        run: |
          python src/scheduler.py --run-once
          
      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          git commit -m "chore: automated daily data refresh [skip ci]" || echo "No changes to commit"
          git push
