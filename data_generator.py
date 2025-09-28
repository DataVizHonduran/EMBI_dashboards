import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import curve_fit
import os
from datetime import datetime

# ETF Data URLs
ETF_URLS = {
    'CEMBI': 'https://www.ishares.com/us/products/239525/ishares-emerging-markets-corporate-bond-etf/1467271812596.ajax?fileType=csv&fileName=CEMB_holdings&dataType=fund',
    'EMBI': 'https://www.ishares.com/us/products/239572/ishares-jp-morgan-usd-emerging-markets-bond-etf/1467271812596.ajax?fileType=csv&fileName=EMB_holdings&dataType=fund',
    'GBI': 'https://www.ishares.com/us/products/239528/ishares-emerging-markets-local-currency-bond-etf/1467271812596.ajax?fileType=csv&fileName=LEMB_holdings&dataType=fund',
    'EMHY': "https://www.ishares.com/us/products/239527/ishares-emerging-markets-high-yield-bond-etf/1467271812596.ajax?fileType=csv&fileName=EMHY_holdings&dataType=fund"
}

# Chart names for display
CHART_NAMES = {
    "EMBI": "iShares J.P. Morgan USD Emerging Markets Bond ETF",
    "CEMBI": "iShares Emerging Markets Corporate Bond ETF", 
    "GBI": "iShares Emerging Markets Local Currency Bond ETF",
    "EMHY": "iShares Emerging Markets High Yield Bond ETF"
}

def fetch_and_clean_data(etf_code):
    """Fetch and clean data for a specific ETF"""
    try:
        print(f"Fetching data for {etf_code}...")
        url = ETF_URLS[etf_code]
        
        # Read CSV starting from row 10 (header=9)
        df = pd.read_csv(url, header=9)
        
        # Create a copy for processing
        new_dfc = df.copy()
        
        # Clean the data - remove rows with 0 weight and limit to top 1000
        new_dfc = new_dfc[pd.to_numeric(new_dfc["Weight (%)"], errors="coerce") != 0].head(1000)
        
        # Convert columns to numeric
        new_dfc["Weight (%)"] = pd.to_numeric(new_dfc["Weight (%)"], errors="coerce")
        new_dfc["YTM (%)"] = pd.to_numeric(new_dfc.get("YTM (%)", np.nan), errors="coerce").round(2)
        new_dfc["Maturity"] = new_dfc["Maturity"].astype(str)
        
        # Remove columns with too many null values
        temp_bool = new_dfc.isnull().sum() > 100
        new_dfc = new_dfc.loc[:, ~temp_bool]
        
        # Remove rows with too many null values
        temp_bool = new_dfc.isnull().sum(axis=1) > 20
        new_dfc = new_dfc.loc[~temp_bool]
        
        # Determine categories for treemap based on available columns
        if {"Location","Maturity"}.issubset(new_dfc.columns):
            categories = ["Location","Name","Maturity"]
        elif {"Location","Sector"}.issubset(new_dfc.columns):
            categories = ["Location","Sector"]
        else:
            categories = ["Location"]
        
        return new_dfc, categories
        
    except Exception as e:
        print(f"Error fetching data for {etf_code}: {str(e)}")
        return None, None

def create_treemap(df, categories, etf_code):
    """Create treemap visualization for an ETF"""
    try:
        # Clean data for visualization
        df_clean = df.dropna(subset=["Weight (%)"])
        df_clean = df_clean[df_clean["Weight (%)"] > 0]
        
        if df_clean.empty:
            print(f"No data available for {etf_code}")
            return None
        
        # Calculate color scale for YTM
        df_des = df_clean["YTM (%)"].fillna(0).describe()
        scale_max = df_des["mean"] + df_des["std"]
        scale_min = df_des["mean"] - df_des["std"]
        
        # Create treemap
        fig = px.treemap(
            df_clean,
            path=categories,
            values="Weight (%)",
            color="YTM (%)",
            color_continuous_scale="RdYlGn_r",
            range_color=[scale_min, scale_max],
            title=f'{CHART_NAMES[etf_code]} - Holdings Treemap'
        )
        
        # Update layout for better appearance
        fig.update_layout(
            title_font_size=16,
            font_size=12,
            height=600,
            margin=dict(t=60, l=25, r=25, b=25)
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating treemap for {etf_code}: {str(e)}")
        return None

def get_etf_summary(df, etf_code):
    """Get summary statistics for an ETF"""
    try:
        df_clean = df.dropna(subset=["Weight (%)"])
        df_clean = df_clean[df_clean["Weight (%)"] > 0]
        
        summary = {
            'total_holdings': len(df_clean),
            'avg_ytm': df_clean["YTM (%)"].fillna(0).mean(),
            'top_holding_weight': df_clean["Weight (%)"].max(),
            'top_5_weight': df_clean.head(5)["Weight (%)"].sum()
        }
        
        return summary
        
    except Exception as e:
        print(f"Error calculating summary for {etf_code}: {str(e)}")
        return None

def generate_charts():
    """Generate all ETF charts and HTML files"""
    print("Starting ETF dashboard generation...")
    
    # Ensure docs directory exists
    os.makedirs('docs', exist_ok=True)
    os.makedirs('docs/charts', exist_ok=True)
    
    etf_info = {}
    
    for etf_code in ETF_URLS.keys():
        print(f"\nProcessing {etf_code}...")
        
        # Fetch and clean data
        df, categories = fetch_and_clean_data(etf_code)
        
        if df is not None and not df.empty:
            # Create treemap
            fig = create_treemap(df, categories, etf_code)
            
            if fig is not None:
                # Save chart as HTML
                fig.write_html(f'docs/charts/{etf_code}.html')
                print(f"Saved chart for {etf_code}")
                
                # Get summary stats
                summary = get_etf_summary(df, etf_code)
                
                etf_info[etf_code] = {
                    'name': CHART_NAMES[etf_code],
                    'summary': summary,
                    'last_updated': datetime.now().isoformat()
                }
            else:
                print(f"Failed to create chart for {etf_code}")
        else:
            print(f"No data available for {etf_code}")
    
    # Generate main dashboard HTML
    generate_dashboard_html(etf_info)
    print("ETF dashboard generation complete!")

def generate_dashboard_html(etf_info):
    """Generate the main index.html for the dashboard"""
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emerging Markets Bond ETF Dashboard</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>📊 Emerging Markets Bond ETF Dashboard</h1>
        <p class="last-updated">Last updated: {datetime.now().strftime('%Y-%m-%d at %H:%M UTC')}</p>
    </header>
    
    <main>
        <div class="controls">
            <label for="etfSelect">Select ETF:</label>
            <select id="etfSelect" onchange="showChart()">
                <option value="">Choose an ETF...</option>
"""
    
    for etf_code, info in etf_info.items():
        html_content += f'                <option value="{etf_code}">{etf_code} - {info["name"]}</option>\n'
    
    html_content += f"""            </select>
        </div>
        
        <div id="chartContainer">
            <div class="placeholder">
                <h3>Welcome to the EM Bond ETF Dashboard!</h3>
                <p>Select an ETF above to view its holdings treemap</p>
                <div class="description">
                    <h4>Available ETFs:</h4>
                    <ul>
                        <li><strong>EMBI</strong> - USD Emerging Markets Bonds</li>
                        <li><strong>CEMBI</strong> - EM Corporate Bonds</li>
                        <li><strong>GBI</strong> - EM Local Currency Bonds</li>
                        <li><strong>EMHY</strong> - EM High Yield Bonds</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="stats">
            <h3>ETF Quick Stats</h3>
            <div class="stats-grid">
"""
    
    for etf_code, info in etf_info.items():
        if info.get('summary'):
            summary = info['summary']
            html_content += f"""                <div class="stat-card">
                    <h4>{etf_code}</h4>
                    <div class="stat-row">
                        <span>Holdings:</span>
                        <span>{summary.get('total_holdings', 'N/A')}</span>
                    </div>
                    <div class="stat-row">
                        <span>Avg YTM:</span>
                        <span>{summary.get('avg_ytm', 0):.2f}%</span>
                    </div>
                    <div class="stat-row">
                        <span>Top 5 Weight:</span>
                        <span>{summary.get('top_5_weight', 0):.1f}%</span>
                    </div>
                </div>
"""
    
    html_content += """            </div>
        </div>
    </main>
    
    <script>
        function showChart() {
            const etf = document.getElementById('etfSelect').value;
            const container = document.getElementById('chartContainer');
            
            if (etf) {
                container.innerHTML = `<iframe src="charts/${etf}.html" width="100%" height="700px" frameborder="0"></iframe>`;
            } else {
                container.innerHTML = `
                    <div class="placeholder">
                        <h3>Welcome to the EM Bond ETF Dashboard!</h3>
                        <p>Select an ETF above to view its holdings treemap</p>
                        <div class="description">
                            <h4>Available ETFs:</h4>
                            <ul>
                                <li><strong>EMBI</strong> - USD Emerging Markets Bonds</li>
                                <li><strong>CEMBI</strong> - EM Corporate Bonds</li>
                                <li><strong>GBI</strong> - EM Local Currency Bonds</li>
                                <li><strong>EMHY</strong> - EM High Yield Bonds</li>
                            </ul>
                        </div>
                    </div>
                `;
            }
        }
    </script>
</body>
</html>"""
    
    with open('docs/index.html', 'w') as f:
        f.write(html_content)

if __name__ == "__main__":
    generate_charts()
