# 🚀 Auê Natural - Automatic Dashboard Updates

## Quick Start Guide

### Option 1: Full Automation (Recommended)

1. **Setup PowerBI credentials** (one-time):
   ```bash
   python setup_powerbi.py
   ```

2. **Run complete pipeline with auto-updates**:
   ```bash
   python run_complete_pipeline.py
   ```

That's it! Your dashboards will automatically update on the front-end when new data is processed.

### Option 2: Manual Pipeline

If you prefer manual control or haven't configured PowerBI yet:

1. **Run matching pipeline**:
   ```bash
   python scripts/automated_matching_pipeline.py
   ```

2. **Manually refresh PowerBI**:
   - Upload files from `./powerbi_data/` to your PowerBI dataset
   - Or use the PowerBI refresh button

## How Automatic Updates Work

```
📊 DATA EXTRACTION → 🔄 MATCHING ENGINE → 📈 DASHBOARD UPDATE
      (Optional)         (Automatic)         (Automatic)
```

When you run the pipeline:

1. **Data Processing**: Runs the enhanced matching engine
2. **File Export**: Copies results to `./powerbi_data/` folder  
3. **API Trigger**: Calls PowerBI REST API to refresh dataset
4. **Dashboard Update**: Front-end dashboards show latest data automatically

## Dashboard Access

Once configured, stakeholders can access updated dashboards at:
- **PowerBI Service**: https://app.powerbi.com/
- **Direct Links**: Your configured workspace dashboards
- **Mobile App**: PowerBI mobile app with latest competitive intelligence

## Benefits of Auto-Updates

✅ **Real-time Intelligence**: Dashboards always show latest competitive data  
✅ **Zero Manual Work**: No need to manually refresh or upload files  
✅ **Stakeholder Friendly**: Business users see updates immediately  
✅ **Production Ready**: Automated pipeline handles all data processing  

## Configuration Files

- `.env` - PowerBI credentials (create with setup_powerbi.py)
- `powerbi_data/` - Auto-generated files for dashboard consumption
- `data/processed/` - Final processed results

## Troubleshooting

**Dashboard not updating?**
1. Check `.env` file has correct credentials
2. Verify `POWERBI_ENABLED=true` 
3. Run `python setup_powerbi.py` to test connection

**Want to disable auto-updates temporarily?**
Set `POWERBI_ENABLED=false` in `.env` file

## Support

The pipeline automatically handles:
- Data extraction and cleaning
- Product matching with AI embeddings  
- Post-processing and merging
- Dashboard data preparation
- PowerBI dataset refresh
- Error handling and logging

Results are logged to `./logs/` for troubleshooting.
