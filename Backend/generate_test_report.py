#!/usr/bin/env python
import os
import sys
import datetime
import subprocess
import webbrowser
from pathlib import Path
import json
import shutil
import platform

def generate_test_report():
    """Generate a comprehensive test report with coverage and insights"""
    print("Generating DocManager Test Report...")
    
    # Create reports directory if it doesn't exist
    reports_dir = Path(__file__).parent / 'reports'
    if not reports_dir.exists():
        reports_dir.mkdir(parents=True)
    
    # Generate timestamp for report
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = reports_dir / f"test_report_{timestamp}"
    report_dir.mkdir(parents=True)
    
    # Path for report files
    html_report = report_dir / "test_report.html"
    coverage_report = report_dir / "coverage"
    json_results = report_dir / "test_results.json"
    
    # Run tests with coverage and store results as JSON
    print("Running tests with coverage...")
    args = [
        sys.executable, 
        "-m", "pytest",
        "tests",
        "-v",
        f"--html={html_report}",
        f"--cov=.",
        f"--cov-report=html:{coverage_report}",
        f"--json={json_results}",
        "--self-contained-html"
    ]
    
    try:
        # Install necessary pytest plugins if not already installed
        subprocess.call([sys.executable, "-m", "pip", "install", "pytest-html", "pytest-json", "pytest-cov", "-q"])
        
        # Run the tests
        result = subprocess.run(args)
        
        # Copy CSS and project logo to report directory
        static_dir = report_dir / "static"
        static_dir.mkdir(exist_ok=True)
        
        # Create custom CSS for better report styling
        with open(static_dir / "custom.css", "w") as css_file:
            css_file.write("""
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            h1, h2, h3 {
                color: #3a4fb5;
            }
            .dashboard {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                margin-bottom: 30px;
            }
            .metric-card {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 15px;
                flex: 1;
                min-width: 200px;
                text-align: center;
            }
            .metric-value {
                font-size: 2em;
                font-weight: bold;
                margin: 10px 0;
            }
            .metric-label {
                color: #6c757d;
                font-size: 0.9em;
            }
            .pass {
                color: #28a745;
            }
            .fail {
                color: #dc3545;
            }
            .skip {
                color: #ffc107;
            }
            .error {
                color: #fd7e14;
            }
            .test-section {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 8px 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }
            th {
                background-color: #f8f9fa;
                font-weight: 600;
            }
            tr:nth-child(even) {
                background-color: #f8f9fa;
            }
            .progress {
                height: 20px;
                background-color: #f2f2f2;
                border-radius: 10px;
                margin: 10px 0;
                overflow: hidden;
            }
            .progress-bar {
                height: 100%;
                border-radius: 10px;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            """)

        # Copy custom report files to the report directory
        custom_css_path = Path(__file__).parent / 'reports' / 'custom_report.css'
        custom_js_path = Path(__file__).parent / 'reports' / 'custom_report.js'
        viewer_path = Path(__file__).parent / 'reports' / 'test_report_viewer.html'
        
        # If custom files don't exist yet, create them
        if not custom_css_path.exists():
            with open(custom_css_path, 'w') as f:
                f.write('/* Custom CSS for test reports will be generated here */')
        
        if not custom_js_path.exists():
            with open(custom_js_path, 'w') as f:
                f.write('// Custom JavaScript for test reports will be generated here')
        
        if not viewer_path.exists():
            with open(viewer_path, 'w') as f:
                f.write('<!-- Custom HTML viewer for test reports will be generated here -->')
        
        # Copy the custom files to the current report directory
        shutil.copy(custom_css_path, report_dir / "custom_report.css")
        shutil.copy(custom_js_path, report_dir / "custom_report.js")
        
        # Create a custom viewer for this report
        with open(report_dir.parent / f"report_viewer_{timestamp}.html", 'w') as f:
            viewer_content = open(viewer_path).read()
            # Update the paths to point to the correct report folder
            viewer_content = viewer_content.replace("test_report_20250510_231150", report_dir.name)
            f.write(viewer_content)
        
        # Create comprehensive report.html with insights
        generate_insights_report(report_dir, json_results, coverage_report)
        
        # Generate PDF report for presentation
        pdf_report = report_dir / "docmanager_test_report.pdf"
        generate_pdf_report(pdf_report, json_results)  # Pass only the JSON results path
        
        # Open report in browser
        insightful_report = report_dir / "insights.html"
        print(f"\nTest report generated at: {insightful_report}")
        print(f"PDF Report for presentation: {pdf_report}")
        print(f"Detailed coverage report: {coverage_report / 'index.html'}")
        
        # Try to open the enhanced viewer instead of just the PDF
        report_viewer = report_dir.parent / f"report_viewer_{timestamp}.html"
        try:
            if platform.system() == 'Windows':
                os.startfile(report_viewer)
            elif platform.system() == 'Darwin':
                subprocess.call(['open', report_viewer])
            else:
                subprocess.call(['xdg-open', report_viewer])
        except:
            pass
        
        return result.returncode
        
    except Exception as e:
        print(f"Error generating test report: {e}")
        return 1

def generate_insights_report(report_dir, json_results, coverage_dir):
    """Generate an insightful HTML report with test result analysis"""
    # Read test results
    try:
        with open(json_results, "r") as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error reading test results: {e}")
        return
    
    # Extract key metrics
    summary = results.get("summary", {})
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    error = summary.get("error", 0)
    xfailed = summary.get("xfailed", 0)
    xpassed = summary.get("xpassed", 0)
    total = summary.get("total", 0)
    
    # Calculate success rate
    success_rate = (passed / total * 100) if total > 0 else 0
    
    # Get test results by category
    tests = results.get("tests", [])
    tests_by_file = {}
    
    for test in tests:
        file_path = test.get("file", "unknown")
        file_name = Path(file_path).name
        
        if file_name not in tests_by_file:
            tests_by_file[file_name] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "error": 0,
                "tests": []
            }
        
        tests_by_file[file_name]["total"] += 1
        tests_by_file[file_name]["tests"].append(test)
        
        outcome = test.get("outcome", "unknown")
        if outcome == "passed":
            tests_by_file[file_name]["passed"] += 1
        elif outcome == "failed":
            tests_by_file[file_name]["failed"] += 1
        elif outcome == "skipped":
            tests_by_file[file_name]["skipped"] += 1
        elif outcome in ["error", "xfailed", "xpassed"]:
            tests_by_file[file_name]["error"] += 1
    
    # Try to parse coverage data
    coverage_data = {}
    try:
        # Look for JSON coverage data
        cov_data_file = list(coverage_dir.glob("coverage*.json"))
        if cov_data_file:
            with open(cov_data_file[0], "r") as f:
                coverage_data = json.load(f)
        
        # If JSON not found, try to read from .coverage file
        elif (coverage_dir.parent / ".coverage").exists():
            pass  # We'd need the coverage module to parse this
    except Exception as e:
        print(f"Error parsing coverage data: {e}")
    
    # Create HTML report with insights
    report_path = report_dir / "insights.html"
    
    with open(report_path, "w") as f:
        # Write HTML header
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocManager Test Insights</title>
    <link rel="stylesheet" href="static/custom.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>DocManager Test Insights</h1>
    <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <div class="dashboard">
        <div class="metric-card">
            <div class="metric-label">Success Rate</div>
            <div class="metric-value" style="color: {'#28a745' if success_rate > 80 else '#ffc107' if success_rate > 50 else '#dc3545'}">{success_rate:.1f}%</div>
            <div class="progress">
                <div class="progress-bar" style="width: {success_rate}%; background-color: {'#28a745' if success_rate > 80 else '#ffc107' if success_rate > 50 else '#dc3545'}">
                    {success_rate:.1f}%
                </div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Tests</div>
            <div class="metric-value">{total}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Passed</div>
            <div class="metric-value pass">{passed}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Failed</div>
            <div class="metric-value fail">{failed}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Skipped</div>
            <div class="metric-value skip">{skipped}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Error</div>
            <div class="metric-value error">{error}</div>
        </div>
    </div>
    
    <div class="test-section">
        <h2>Test Results Summary</h2>
        <canvas id="testResultsChart" width="400" height="200"></canvas>
    </div>
    
    <div class="test-section">
        <h2>Test Results by File</h2>
        <table>
            <tr>
                <th>Test File</th>
                <th>Total</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Skipped</th>
                <th>Error</th>
                <th>Success Rate</th>
            </tr>
""")
        
        # Write test results by file
        for file_name, data in tests_by_file.items():
            file_success_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
            f.write(f"""
            <tr>
                <td>{file_name}</td>
                <td>{data["total"]}</td>
                <td class="pass">{data["passed"]}</td>
                <td class="fail">{data["failed"]}</td>
                <td class="skip">{data["skipped"]}</td>
                <td class="error">{data["error"]}</td>
                <td>
                    <div class="progress" style="width: 100%">
                        <div class="progress-bar" style="width: {file_success_rate}%; background-color: {'#28a745' if file_success_rate > 80 else '#ffc107' if file_success_rate > 50 else '#dc3545'}">
                            {file_success_rate:.1f}%
                        </div>
                    </div>
                </td>
            </tr>""")
        
        f.write("""
        </table>
    </div>
    
    <div class="test-section">
        <h2>Module Test Results</h2>
        <p>Detailed breakdown of test success by module:</p>
        <canvas id="moduleChart" width="400" height="300"></canvas>
    </div>
""")

        # Write all test cases and results
        f.write("""
    <div class="test-section">
        <h2>All Test Cases</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Status</th>
                <th>Duration (s)</th>
            </tr>
""")
        
        for test in tests:
            name = test.get("name", "Unknown")
            outcome = test.get("outcome", "unknown")
            duration = test.get("duration", 0)
            
            outcome_class = ""
            if outcome == "passed":
                outcome_class = "pass"
            elif outcome == "failed":
                outcome_class = "fail"
            elif outcome == "skipped":
                outcome_class = "skip"
            else:
                outcome_class = "error"
            
            f.write(f"""
            <tr>
                <td>{name}</td>
                <td class="{outcome_class}">{outcome.upper()}</td>
                <td>{duration:.3f}</td>
            </tr>""")
        
        f.write("""
        </table>
    </div>
""")

        # Add insights section
        f.write("""
    <div class="test-section">
        <h2>Testing Insights</h2>
        
        <h3>Strengths</h3>
        <ul>
""")
        # Add strength insights
        if success_rate > 70:
            f.write("<li>Overall high pass rate shows good code quality and test coverage.</li>")
        
        if passed > 0:
            f.write("<li>Core functions including encryption and blockchain connections are working properly.</li>")
        
        # Find which areas have 100% success
        perfect_modules = [file for file, data in tests_by_file.items() 
                          if data["total"] > 0 and data["passed"] == data["total"]]
        
        if perfect_modules:
            f.write("<li>The following modules show 100% test success: " + 
                   ", ".join(perfect_modules) + "</li>")
        
        f.write("""
        </ul>
        
        <h3>Areas for Improvement</h3>
        <ul>
""")
        # Add improvement insights
        if failed > 0:
            f.write("<li>Some tests are failing and need attention.</li>")
            
        # Find which areas have failures
        failing_modules = [file for file, data in tests_by_file.items() 
                          if data["failed"] > 0]
        
        if failing_modules:
            f.write("<li>The following modules have failing tests that need attention: " + 
                   ", ".join(failing_modules) + "</li>")
            
        if skipped > 0:
            f.write("<li>Some tests are being skipped, consider implementing them for better coverage.</li>")
            
        f.write("""
        </ul>
        
        <h3>Recommendations</h3>
        <ul>
""")
        # Add recommendations
        f.write("<li>Focus on fixing failing tests to improve overall quality.</li>")
        f.write("<li>Consider adding more test cases for better code coverage.</li>")
        
        if 'test_blockchain_logger.py' in tests_by_file:
            f.write("<li>Ensure Ganache is running and properly configured for blockchain tests.</li>")
        
        f.write("""
        </ul>
    </div>
    
    <div class="test-section">
        <h2>Navigation</h2>
        <ul>
            <li><a href="test_report.html">View Detailed Test Report</a></li>
            <li><a href="coverage/index.html">View Coverage Report</a></li>
        </ul>
    </div>

    <script>
        // Create test results chart
        const testResultsCtx = document.getElementById('testResultsChart').getContext('2d');
        new Chart(testResultsCtx, {
            type: 'pie',
            data: {
                labels: ['Passed', 'Failed', 'Skipped', 'Error'],
                datasets: [{
                    data: [""" + f"{passed}, {failed}, {skipped}, {error}" + """],
                    backgroundColor: [
                        '#28a745',
                        '#dc3545',
                        '#ffc107',
                        '#fd7e14'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Test Result Distribution'
                    }
                }
            }
        });
        
        // Create module chart
        const moduleCtx = document.getElementById('moduleChart').getContext('2d');
        new Chart(moduleCtx, {
            type: 'bar',
            data: {
                labels: [""" + ", ".join([f"'{file}'" for file in tests_by_file.keys()]) + """],
                datasets: [
                    {
                        label: 'Passed',
                        backgroundColor: '#28a745',
                        data: [""" + ", ".join([str(data["passed"]) for data in tests_by_file.values()]) + """]
                    },
                    {
                        label: 'Failed',
                        backgroundColor: '#dc3545',
                        data: [""" + ", ".join([str(data["failed"]) for data in tests_by_file.values()]) + """]
                    },
                    {
                        label: 'Skipped',
                        backgroundColor: '#ffc107',
                        data: [""" + ", ".join([str(data["skipped"]) for data in tests_by_file.values()]) + """]
                    },
                    {
                        label: 'Error',
                        backgroundColor: '#fd7e14',
                        data: [""" + ", ".join([str(data["error"]) for data in tests_by_file.values()]) + """]
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        stacked: true,
                    },
                    y: {
                        stacked: true
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Test Results by Module'
                    }
                }
            }
        });
    </script>
</body>
</html>
""")

def generate_pdf_report(pdf_path, json_results_path):
    """Generate a professional PDF report suitable for presentations"""
    try:
        # Install reportlab if needed
        try:
            import reportlab
        except ImportError:
            print("Installing ReportLab for PDF generation...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "-q"])
            
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.lib.units import inch
        
        print("Generating PDF report...")
        
        # Read test results
        try:
            with open(json_results_path, "r") as f:
                results = json.load(f)
        except Exception as e:
            print(f"Error reading test results for PDF generation: {e}")
            return
        
        # Extract key metrics
        summary = results.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        error = summary.get("error", 0)
        total = summary.get("total", 0)
        
        # Calculate success rate
        success_rate = (passed / total * 100) if total > 0 else 0
        
        # Get test results by category
        tests = results.get("tests", [])
        tests_by_file = {}
        
        for test in tests:
            file_path = test.get("file", "unknown")
            file_name = Path(file_path).name
            
            if file_name not in tests_by_file:
                tests_by_file[file_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "error": 0,
                    "tests": []
                }
            
            tests_by_file[file_name]["total"] += 1
            tests_by_file[file_name]["tests"].append(test)
            
            outcome = test.get("outcome", "unknown")
            if outcome == "passed":
                tests_by_file[file_name]["passed"] += 1
            elif outcome == "failed":
                tests_by_file[file_name]["failed"] += 1
            elif outcome == "skipped":
                tests_by_file[file_name]["skipped"] += 1
            elif outcome in ["error", "xfailed", "xpassed"]:
                tests_by_file[file_name]["error"] += 1
        
        # Create the PDF document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        heading2_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Create custom styles
        subtitle_style = ParagraphStyle(
            'Subtitle', 
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12
        )
        
        table_title_style = ParagraphStyle(
            'TableTitle', 
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.darkblue,
            spaceBefore=6,
            spaceAfter=6
        )
        
        # Add title
        elements.append(Paragraph("DocManager Test Report", title_style))
        elements.append(Spacer(1, 12))
        
        # Add date
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated on {date_str}", normal_style))
        elements.append(Spacer(1, 24))
        
        # Add executive summary
        elements.append(Paragraph("Executive Summary", heading2_style))
        elements.append(Spacer(1, 6))
        
        summary_text = f"""
        This report presents the test results for the DocManager application. The tests cover various components
        including encryption, blockchain integration, document handling, and user authentication. 
        
        The overall test success rate is {success_rate:.1f}%. Out of {passed + failed + skipped + error} total tests:
        • {passed} tests passed successfully
        • {failed} tests failed
        • {skipped} tests were skipped
        • {error} tests resulted in errors
        """
        elements.append(Paragraph(summary_text, normal_style))
        elements.append(Spacer(1, 12))
        
        # Create a pie chart for test results
        drawing = Drawing(400, 200)
        pie = Pie()
        pie.x = 150
        pie.y = 65
        pie.width = 170
        pie.height = 170
        pie.data = [passed, failed, skipped, error]
        pie.labels = ['Passed', 'Failed', 'Skipped', 'Error']
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = colors.green
        pie.slices[1].fillColor = colors.red
        pie.slices[2].fillColor = colors.yellow
        pie.slices[3].fillColor = colors.orange
        drawing.add(pie)
        elements.append(drawing)
        
        # Add tests by module section
        elements.append(Paragraph("Test Results by Module", heading2_style))
        elements.append(Spacer(1, 6))
        
        # Create test results table
        test_table_data = [
            ['Module', 'Total', 'Passed', 'Failed', 'Skipped', 'Error', 'Success Rate']
        ]
        
        # Add data for each module
        for file_name, data in tests_by_file.items():
            file_success_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
            test_table_data.append([
                file_name, 
                data["total"],
                data["passed"],
                data["failed"],
                data["skipped"],
                data["error"],
                f"{file_success_rate:.1f}%"
            ])
        
        # Create the table
        test_table = Table(test_table_data, repeatRows=1)
        
        # Style the table
        test_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
            # Highlight success rates
            ('TEXTCOLOR', (6,1), (6,-1), colors.green),
        ]))
        
        elements.append(test_table)
        elements.append(Spacer(1, 24))
        
        # Add key insights section
        elements.append(Paragraph("Key Insights", heading2_style))
        elements.append(Spacer(1, 6))
        
        # Strengths
        elements.append(Paragraph("Strengths:", subtitle_style))
        strengths = []
        
        if success_rate > 70:
            strengths.append("• Overall high pass rate shows good code quality and test coverage.")
        
        if passed > 0:
            strengths.append("• Core functions including encryption and blockchain connections are working properly.")
        
        # Find which areas have 100% success
        perfect_modules = [file for file, data in tests_by_file.items() 
                          if data["total"] > 0 and data["passed"] == data["total"]]
        
        if perfect_modules:
            strengths.append("• The following modules show 100% test success: " + 
                           ", ".join(perfect_modules))
        
        for strength in strengths:
            elements.append(Paragraph(strength, normal_style))
        
        elements.append(Spacer(1, 12))
        
        # Areas for improvement
        elements.append(Paragraph("Areas for Improvement:", subtitle_style))
        improvements = []
        
        if failed > 0:
            improvements.append("• Some tests are failing and need attention.")
            
        # Find which areas have failures
        failing_modules = [file for file, data in tests_by_file.items() 
                          if data["failed"] > 0]
        
        if failing_modules:
            improvements.append("• The following modules have failing tests that need attention: " + 
                              ", ".join(failing_modules))
            
        if skipped > 0:
            improvements.append("• Some tests are being skipped, consider implementing them for better coverage.")
        
        for improvement in improvements:
            elements.append(Paragraph(improvement, normal_style))
        
        elements.append(Spacer(1, 12))
        
        # Recommendations
        elements.append(Paragraph("Recommendations:", subtitle_style))
        recommendations = [
            "• Focus on fixing failing tests to improve overall quality.",
            "• Consider adding more test cases for better code coverage."
        ]
        
        if 'test_blockchain_logger.py' in tests_by_file:
            recommendations.append("• Ensure Ganache is running and properly configured for blockchain tests.")
        
        for recommendation in recommendations:
            elements.append(Paragraph(recommendation, normal_style))
        
        elements.append(PageBreak())
        
        # Detailed test results
        elements.append(Paragraph("Detailed Test Results", heading2_style))
        elements.append(Spacer(1, 6))
        
        # Extract tests from results
        tests = results.get("tests", [])
        
        # Create test results table
        detailed_table_data = [
            ['Test Name', 'Status', 'Duration (s)']
        ]
        
        # Sort tests by outcome
        tests.sort(key=lambda t: (
            0 if t.get("outcome") == "passed" else
            1 if t.get("outcome") == "failed" else
            2 if t.get("outcome") == "skipped" else 3
        ))
        
        # Add each test to the table
        for test in tests:
            name = test.get("name", "Unknown")
            outcome = test.get("outcome", "unknown")
            duration = test.get("duration", 0)
            
            detailed_table_data.append([
                name,
                outcome.upper(),
                f"{duration:.3f}"
            ])
        
        # Create the table with repeating header row
        detailed_table = Table(detailed_table_data, repeatRows=1)
        
        # Style the table
        detailed_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('ALIGN', (2,1), (2,-1), 'RIGHT'),
        ]))
        
        # Color code based on outcome
        for i, test in enumerate(tests, 1):
            outcome = test.get("outcome", "")
            if outcome == "passed":
                detailed_table.setStyle(TableStyle([('TEXTCOLOR', (1,i), (1,i), colors.green)]))
            elif outcome == "failed":
                detailed_table.setStyle(TableStyle([('TEXTCOLOR', (1,i), (1,i), colors.red)]))
            elif outcome == "skipped":
                detailed_table.setStyle(TableStyle([('TEXTCOLOR', (1,i), (1,i), colors.orange)]))
                
        elements.append(detailed_table)
        
        # Build the PDF
        doc.build(elements)
        print(f"PDF report successfully generated at: {pdf_path}")
        
    except Exception as e:
        print(f"Error generating PDF report: {e}")
        # If an error occurs, try to install reportlab again
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "reportlab", "pillow"])
            print("Please try running the report generation again.")
        except:
            pass

if __name__ == "__main__":
    sys.exit(generate_test_report())
