"""
FastAPI web application with Vercel Web Analytics integration.
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with Vercel Web Analytics."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deriv Trading Toolkit</title>
    <script>
        window.va = window.va || function () { 
            (window.vaq = window.vaq || []).push(arguments); 
        };
    </script>
    <script defer src="/_vercel/insights/script.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #333;
        }
        h1 {
            color: #0070f3;
            border-bottom: 2px solid #0070f3;
            padding-bottom: 0.5rem;
        }
        .section {
            background: #f5f5f5;
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        code {
            background: #e0e0e0;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        .warning {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 1rem;
            margin: 1rem 0;
        }
        a {
            color: #0070f3;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        ul {
            margin: 0.5rem 0;
        }
    </style>
</head>
<body>
    <h1>🔧 Deriv Trading Toolkit</h1>
    
    <div class="warning">
        <strong>⚠️ Important Notice:</strong>
        <p>Synthetic indices and accumulators carry real financial risk. This toolkit is for educational purposes only and does not constitute financial advice. Always start with a demo account.</p>
    </div>

    <div class="section">
        <h2>📊 About This Toolkit</h2>
        <p>A Python-based toolkit for <a href="https://deriv.com" target="_blank">Deriv</a> synthetic-index trading, featuring:</p>
        <ul>
            <li>Market and tick analysis</li>
            <li>Account dashboard</li>
            <li>Accumulator backtester</li>
            <li>Automated trading bot (with safety controls)</li>
        </ul>
    </div>

    <div class="section">
        <h2>🚀 Available Commands</h2>
        <p><strong>Analysis:</strong> <code>python main.py analyze --symbol R_100 --count 1000</code></p>
        <p><strong>Dashboard:</strong> <code>python main.py dashboard</code></p>
        <p><strong>Backtest:</strong> <code>python main.py backtest --symbol R_100 --stake 1 --growth-rate 0.03</code></p>
        <p><strong>Bot (Dry Run):</strong> <code>python main.py bot --symbol R_100 --stake 1 --growth-rate 0.02</code></p>
    </div>

    <div class="section">
        <h2>📖 Documentation</h2>
        <p>For complete setup instructions, API usage, and safety guidelines, please refer to the <a href="https://github.com/fahadramadhan87-eng/tradertool.pro" target="_blank">GitHub repository</a>.</p>
    </div>

    <footer style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; text-align: center; color: #666;">
        <p>Powered by FastAPI • Deployed on Vercel • <a href="/docs" target="_blank">API Documentation</a></p>
    </footer>
</body>
</html>
"""


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "deriv-toolkit"}


@app.get("/api/info")
async def info():
    """Service information endpoint."""
    return {
        "name": "Deriv Trading Toolkit",
        "version": "0.1.0",
        "framework": "FastAPI",
        "analytics": "Vercel Web Analytics",
        "endpoints": {
            "root": "/",
            "health": "/api/health",
            "info": "/api/info",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }
