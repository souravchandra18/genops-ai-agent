#!/usr/bin/env python3
"""
Dynamic Enhanced Analysis Results Processor
Combines dynamic tool detection with advanced visualizations
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from datetime import datetime
from tabulate import tabulate
from collections import Counter
from dynamic_processor import DynamicAnalysisProcessor

class EnhancedDynamicProcessor(DynamicAnalysisProcessor):
    def __init__(self, input_file=None):
        repo_root = Path.cwd()
        resolved_input = input_file or (
            repo_root / "analysis_results" / "analyzer_results_convert.md"
        )
        super().__init__(resolved_input)

        
    def create_enhanced_reports(self):
        """Create all enhanced output formats with visualizations"""
        if not self.processed_data:
            print("❌ No data to process")
            return
        
        # Create output directories
        output_dir = Path('enhanced_dynamic_results')
        output_dir.mkdir(exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create DataFrame
        df = pd.DataFrame(self.processed_data)
        
        # Generate enhanced reports
        self._create_enhanced_excel_report(df, output_dir, timestamp)
        self._create_enhanced_html_report(df, output_dir, timestamp)
        self._create_advanced_visualizations(df, output_dir, timestamp)
        self._create_detailed_text_summary(df, output_dir, timestamp)
        
        print(f"\n🎉 Enhanced reports generated in '{output_dir}' directory!")
        print(f"📊 Total violations: {len(self.processed_data)}")
        print(f"🔧 Tools processed: {len([t for t, d in self.tools_data.items() if d])}")
        
    def _create_enhanced_excel_report(self, df, output_dir, timestamp):
        """Create Excel report with advanced formatting and charts"""
        excel_file = output_dir / f"enhanced_analysis_{timestamp}.xlsx"
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Summary dashboard
            summary_data = []
            for tool, data in self.tools_data.items():
                if data:
                    severities = [item['Severity'] for item in data if item['Severity']]
                    files = [item['File'] for item in data if item['File']]
                    
                    summary_data.append({
                        'Tool': tool,
                        'Total_Issues': len(data),
                        'Files_Affected': len(set(files)),
                        'High_Priority': len([s for s in severities if any(term in str(s).upper() for term in ['HIGH', 'ERROR', 'CRITICAL'])]),
                        'Medium_Priority': len([s for s in severities if any(term in str(s).upper() for term in ['MEDIUM', 'WARN', 'WARNING'])]),
                        'Low_Priority': len([s for s in severities if any(term in str(s).upper() for term in ['LOW', 'INFO'])]),
                        'Most_Common_Rule': self._get_most_common_rule(data)
                    })
            
            if summary_data:
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Dashboard', index=False)
            
            # Individual tool sheets with formatting
            for tool, data in self.tools_data.items():
                if data:
                    tool_df = pd.DataFrame(data)
                    sheet_name = tool[:31]
                    tool_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # File-based analysis
            if not df.empty:
                file_analysis = df.groupby('File').agg({
                    'Tool': 'count',
                    'Severity': lambda x: ', '.join(x.unique()[:3])
                }).rename(columns={'Tool': 'Issue_Count', 'Severity': 'Severity_Types'})
                file_analysis = file_analysis.sort_values('Issue_Count', ascending=False)
                file_analysis.to_excel(writer, sheet_name='File_Analysis')
        
        print(f"📊 Enhanced Excel: {excel_file}")
    
    def _get_most_common_rule(self, data):
        """Get the most common rule for a tool"""
        rules = [item['Rule'] for item in data if item['Rule']]
        if rules:
            return Counter(rules).most_common(1)[0][0]
        return 'N/A'
    
    def _create_enhanced_html_report(self, df, output_dir, timestamp):
        """Create comprehensive HTML report with embedded charts"""
        html_file = output_dir / f"enhanced_report_{timestamp}.html"
        
        # Create chart files first
        chart_files = []
        if not df.empty:
            chart_files = self._create_embedded_charts(df, output_dir, timestamp)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Dynamic Analysis Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
        .summary {{ background-color: #ecf0f1; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .tool-section {{ margin: 30px 0; border: 1px solid #bdc3c7; border-radius: 8px; overflow: hidden; }}
        .tool-header {{ background-color: #3498db; color: white; padding: 15px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; table-layout: fixed; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; word-wrap: break-word; overflow-wrap: break-word; }}
        th {{ background-color: #34495e; color: white; }}
        td.message-col {{ max-width: 400px; white-space: pre-wrap; word-break: break-word; }}
        td.file-col {{ max-width: 300px; word-break: break-all; }}
        td.tool-col {{ width: 80px; }}
        td.severity-col {{ width: 100px; }}
        td.line-col {{ width: 60px; text-align: center; }}
        td.column-col {{ width: 60px; text-align: center; }}
        .severity-high {{ background-color: #ffebee; }}
        .severity-medium {{ background-color: #fff3e0; }}
        .severity-low {{ background-color: #f1f8e9; }}
        .chart-container {{ text-align: center; margin: 20px 0; }}
        .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #e74c3c; }}
        .metric-label {{ color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Enhanced Dynamic Analysis Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Powered by Dynamic Analysis Processor</p>
    </div>
    
    <div class="summary">
        <h2>📊 Executive Summary</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{len(self.processed_data)}</div>
                <div class="metric-label">Total Issues</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len([t for t, d in self.tools_data.items() if d])}</div>
                <div class="metric-label">Tools Analyzed</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(set(item['File'] for item in self.processed_data if item['File']))}</div>
                <div class="metric-label">Files Affected</div>
            </div>
        </div>
    </div>
"""
        
        # Add charts if available
        for chart_file in chart_files:
            html_content += f"""
    <div class="chart-container">
        <img src="{chart_file.name}" alt="Analysis Chart" style="max-width: 100%; height: auto;">
    </div>
"""
        
        # Add tool-specific sections with improved table formatting
        for tool, data in self.tools_data.items():
            if data:
                # Create DataFrame with better formatting
                tool_df = pd.DataFrame(data)
                
                # Generate table HTML with custom classes
                table_html = tool_df.to_html(escape=False, classes='table', table_id=f'table-{tool.lower()}')
                
                # Add custom CSS classes to columns
                table_html = table_html.replace('<td>', '<td class="message-col">')
                table_html = table_html.replace('border="1"', '')
                
                # Apply specific column classes
                lines = table_html.split('\n')
                improved_lines = []
                
                for line in lines:
                    if '<td' in line and not 'class=' in line:
                        # Detect column content and apply appropriate class
                        if any(keyword in line for keyword in ['PMD', 'CHECKSTYLE', 'TRIVY', 'SEMGREP', 'SPOTBUGS']):
                            line = line.replace('<td>', '<td class="tool-col">')
                        elif any(keyword in line for keyword in ['Priority', 'WARN', 'ERROR', 'INFO', 'HIGH', 'MEDIUM', 'LOW']):
                            line = line.replace('<td>', '<td class="severity-col">')
                        elif line.count('/') > 2 or '.java' in line or '.xml' in line:  # File paths
                            line = line.replace('<td>', '<td class="file-col">')
                        elif line.strip().replace('<td>', '').replace('</td>', '').isdigit():  # Line/column numbers
                            line = line.replace('<td>', '<td class="line-col">')
                        else:
                            line = line.replace('<td>', '<td class="message-col">')
                    
                    improved_lines.append(line)
                
                table_html = '\n'.join(improved_lines)
                
                html_content += f"""
    <div class="tool-section">
        <div class="tool-header">🔧 {tool} ({len(data)} issues)</div>
        {table_html}
    </div>
"""
        
        html_content += """
    <script>
        // Add row highlighting on hover and improve message display
        document.querySelectorAll('tr').forEach(row => {
            row.addEventListener('mouseenter', () => row.style.backgroundColor = '#f8f9fa');
            row.addEventListener('mouseleave', () => row.style.backgroundColor = '');
        });
        
        // Add click to expand long messages
        document.querySelectorAll('td.message-col').forEach(cell => {
            if (cell.textContent.length > 100) {
                cell.style.cursor = 'pointer';
                cell.title = 'Click to expand';
                let isExpanded = false;
                let originalText = cell.textContent;
                let truncatedText = originalText.substring(0, 100) + '...';
                
                cell.textContent = truncatedText;
                
                cell.addEventListener('click', () => {
                    if (isExpanded) {
                        cell.textContent = truncatedText;
                        cell.title = 'Click to expand';
                    } else {
                        cell.textContent = originalText;
                        cell.title = 'Click to collapse';
                    }
                    isExpanded = !isExpanded;
                });
            }
        });
    </script>
</body>
</html>
"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🌐 Enhanced HTML: {html_file}")
    
    def _create_embedded_charts(self, df, output_dir, timestamp):
        """Create charts for embedding in HTML report"""
        chart_files = []
        
        if df.empty:
            return chart_files
        
        plt.style.use('seaborn-v0_8')
        
        # Chart 1: Tool Distribution Pie Chart
        fig, ax = plt.subplots(figsize=(10, 8))
        tool_counts = df['Tool'].value_counts()
        colors = plt.cm.Set3(np.linspace(0, 1, len(tool_counts)))
        wedges, texts, autotexts = ax.pie(tool_counts.values, labels=tool_counts.index, autopct='%1.1f%%', colors=colors)
        ax.set_title('Distribution of Issues by Tool', fontsize=16, fontweight='bold')
        
        chart1 = output_dir / f"tool_distribution_{timestamp}.png"
        plt.savefig(chart1, dpi=300, bbox_inches='tight', facecolor='white')
        chart_files.append(chart1)
        plt.close()
        
        # Chart 2: Severity Analysis
        if 'Severity' in df.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            severity_counts = df['Severity'].value_counts()
            bars = ax.bar(range(len(severity_counts)), severity_counts.values, color=['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71'])
            ax.set_xticks(range(len(severity_counts)))
            ax.set_xticklabels(severity_counts.index, rotation=45)
            ax.set_title('Issue Distribution by Severity', fontsize=16, fontweight='bold')
            ax.set_ylabel('Number of Issues')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{int(height)}', ha='center', va='bottom')
            
            chart2 = output_dir / f"severity_analysis_{timestamp}.png"
            plt.savefig(chart2, dpi=300, bbox_inches='tight', facecolor='white')
            chart_files.append(chart2)
            plt.close()
        
        return chart_files
    
    def _create_advanced_visualizations(self, df, output_dir, timestamp):
        """Create advanced visualization dashboard"""
        if df.empty:
            return
        
        plt.style.use('default')
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('🔍 Advanced Dynamic Analysis Dashboard', fontsize=20, fontweight='bold')
        
        # 1. Tool Distribution
        if not df.empty:
            tool_counts = df['Tool'].value_counts()
            axes[0, 0].pie(tool_counts.values, labels=tool_counts.index, autopct='%1.1f%%', startangle=90)
            axes[0, 0].set_title('Tool Distribution')
        
        # 2. Files with Most Issues
        if 'File' in df.columns:
            file_counts = df['File'].value_counts().head(10)
            if not file_counts.empty:
                y_pos = np.arange(len(file_counts))
                axes[0, 1].barh(y_pos, file_counts.values)
                axes[0, 1].set_yticks(y_pos)
                axes[0, 1].set_yticklabels([f.split('/')[-1][:20] for f in file_counts.index])
                axes[0, 1].set_title('Top 10 Files by Issue Count')
        
        # 3. Severity Trends
        severity_counts = df['Severity'].value_counts()
        axes[0, 2].bar(range(len(severity_counts)), severity_counts.values)
        axes[0, 2].set_xticks(range(len(severity_counts)))
        axes[0, 2].set_xticklabels(severity_counts.index, rotation=45)
        axes[0, 2].set_title('Severity Distribution')
        
        # 4. Tool vs Severity Heatmap
        if len(df) > 0:
            pivot_table = df.groupby(['Tool', 'Severity']).size().unstack(fill_value=0)
            if not pivot_table.empty:
                sns.heatmap(pivot_table, annot=True, fmt='d', cmap='YlOrRd', ax=axes[1, 0])
                axes[1, 0].set_title('Tool vs Severity Heatmap')
        
        # 5. Rule Frequency
        if 'Rule' in df.columns:
            rule_counts = df[df['Rule'] != '']['Rule'].value_counts().head(10)
            if not rule_counts.empty:
                axes[1, 1].barh(range(len(rule_counts)), rule_counts.values)
                axes[1, 1].set_yticks(range(len(rule_counts)))
                axes[1, 1].set_yticklabels([r[:30] for r in rule_counts.index])
                axes[1, 1].set_title('Top 10 Most Frequent Rules')
        
        # 6. File Type Analysis
        if 'File' in df.columns:
            extensions = [f.split('.')[-1] if '.' in f else 'unknown' for f in df['File'] if f]
            ext_counts = pd.Series(extensions).value_counts().head(8)
            if not ext_counts.empty:
                axes[1, 2].pie(ext_counts.values, labels=ext_counts.index, autopct='%1.1f%%')
                axes[1, 2].set_title('Issues by File Type')
        
        plt.tight_layout()
        chart_file = output_dir / f"advanced_dashboard_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📈 Advanced Dashboard: {chart_file}")
    
    def _create_detailed_text_summary(self, df, output_dir, timestamp):
        """Create detailed text summary with statistics"""
        text_file = output_dir / f"detailed_summary_{timestamp}.txt"
        
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("🔍 ENHANCED DYNAMIC ANALYSIS SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Issues Found: {len(self.processed_data)}\n")
            f.write(f"Analysis Tools Used: {len([t for t, d in self.tools_data.items() if d])}\n")
            f.write(f"Files Analyzed: {len(set(item['File'] for item in self.processed_data if item['File']))}\n\n")
            
            # Detailed tool breakdown
            f.write("🔧 DETAILED TOOL ANALYSIS\n")
            f.write("-" * 40 + "\n")
            
            for tool, data in self.tools_data.items():
                if data:
                    f.write(f"\n{tool}:\n")
                    f.write(f"  📊 Total Issues: {len(data)}\n")
                    
                    # Severity breakdown
                    severities = [item['Severity'] for item in data if item['Severity']]
                    if severities:
                        severity_counts = Counter(severities)
                        f.write("  🎯 Severity Breakdown:\n")
                        for severity, count in severity_counts.most_common():
                            f.write(f"    - {severity}: {count}\n")
                    
                    # Top rules
                    rules = [item['Rule'] for item in data if item['Rule']]
                    if rules:
                        rule_counts = Counter(rules)
                        f.write("  📋 Top Rules:\n")
                        for rule, count in rule_counts.most_common(3):
                            f.write(f"    - {rule}: {count} occurrences\n")
                    
                    # Affected files
                    files = [item['File'] for item in data if item['File']]
                    if files:
                        file_counts = Counter(files)
                        f.write("  📁 Most Affected Files:\n")
                        for file, count in file_counts.most_common(3):
                            filename = file.split('/')[-1]
                            f.write(f"    - {filename}: {count} issues\n")
            
            # Cross-tool analysis
            if len(self.tools_data) > 1:
                f.write(f"\n🔄 CROSS-TOOL ANALYSIS\n")
                f.write("-" * 30 + "\n")
                
                all_files = set()
                for data in self.tools_data.values():
                    all_files.update(item['File'] for item in data if item['File'])
                
                multi_tool_files = []
                for file in all_files:
                    affecting_tools = []
                    for tool, data in self.tools_data.items():
                        if any(item['File'] == file for item in data):
                            affecting_tools.append(tool)
                    if len(affecting_tools) > 1:
                        multi_tool_files.append((file, affecting_tools))
                
                if multi_tool_files:
                    f.write(f"Files flagged by multiple tools ({len(multi_tool_files)}):\n")
                    for file, tools in multi_tool_files[:5]:
                        filename = file.split('/')[-1]
                        f.write(f"  - {filename}: {', '.join(tools)}\n")
        
        print(f"📄 Detailed Summary: {text_file}")

def main():
    print("🚀 Starting Enhanced Dynamic Processing...")
    
    processor = EnhancedDynamicProcessor()
    
    # Extract data from all tools
    processor.extract_tool_data()
    
    # Create enhanced reports
    processor.create_enhanced_reports()
    
    print("\n✅ Enhanced dynamic processing complete!")

if __name__ == "__main__":
    main()