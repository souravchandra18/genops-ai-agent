#!/usr/bin/env python3
"""
Dynamic Analysis Results Processor
Automatically processes ANY tool's results from markdown with JSON blocks
"""

import json
import pandas as pd
from datetime import datetime
import re
from pathlib import Path
from tabulate import tabulate
import matplotlib.pyplot as plt
import seaborn as sns

class DynamicAnalysisProcessor:
    def __init__(self, input_file=None):
        repo_root = Path.cwd()
        self.input_file = input_file or (
            repo_root / "analysis_results" / "analyzer_results_convert.md"
        )
        self.tools_data = {}
        self.processed_data = []
        
    def extract_tool_data(self):
        """Dynamically extract data from ANY tool mentioned in the markdown file"""
        with open(self.input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Find tool sections dynamically - improved pattern
        tool_pattern = r'## 🔧 (\w+)(.*?)(?=## 🔧|\Z)'
        tool_matches = re.findall(tool_pattern, content, re.DOTALL)
        
        print(f"🔍 Found {len(tool_matches)} tool sections")
        
        for tool_name, tool_section in tool_matches:
            tool_name = tool_name.upper()
            print(f"📋 Processing {tool_name}...")
            
            # Extract JSON blocks from this tool section
            json_pattern = r'<details>.*?```json\n(.*?)\n```.*?</details>'
            json_matches = re.findall(json_pattern, tool_section, re.DOTALL)
            
            tool_data = []
            for match in json_matches:
                try:
                    json_obj = json.loads(match)
                    violations = self._extract_violations_dynamically(tool_name, json_obj)
                    tool_data.extend(violations)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Error parsing JSON for {tool_name}: {e}")
            
            # Also check for text-based warnings (like Checkstyle)
            text_violations = self._extract_text_violations(tool_name, tool_section)
            tool_data.extend(text_violations)
            
            self.tools_data[tool_name] = tool_data
            self.processed_data.extend(tool_data)
            
            print(f"✅ {tool_name}: {len(tool_data)} violations found")
        
        return self.tools_data
    
    def _extract_violations_dynamically(self, tool_name, json_data):
        """Dynamically extract violations from any JSON structure"""
        violations = []
        
        # Handle different JSON structures automatically
        if isinstance(json_data, list):
            for item in json_data:
                violations.extend(self._process_item(tool_name, item))
        elif isinstance(json_data, dict):
            violations.extend(self._process_dict(tool_name, json_data))
        
        return violations
    
    def _process_dict(self, tool_name, data, parent_key=''):
        """Process dictionary structure recursively"""
        violations = []
        
        # Look for common violation containers
        violation_keys = ['violations', 'files', 'results', 'Results', 'findings', 'issues', 'bugs', 'BugInstance', 'Vulnerabilities']
        
        for key, value in data.items():
            if key in violation_keys:
                if isinstance(value, list):
                    for item in value:
                        violations.extend(self._process_violation_item(tool_name, item, key))
                elif isinstance(value, dict):
                    violations.extend(self._process_violation_item(tool_name, value, key))
            elif isinstance(value, (dict, list)):
                violations.extend(self._process_item(tool_name, value))
        
        return violations
    
    def _process_item(self, tool_name, item):
        """Process individual items"""
        if isinstance(item, dict):
            return self._process_dict(tool_name, item)
        elif isinstance(item, list):
            violations = []
            for sub_item in item:
                violations.extend(self._process_item(tool_name, sub_item))
            return violations
        return []
    
    def _process_violation_item(self, tool_name, item, context=''):
        """Process individual violation items"""
        violations = []
        
        if isinstance(item, dict):
            # Extract violation data dynamically
            violation = {
                'Tool': tool_name,
                'Severity': self._get_field_value(item, ['severity', 'priority', 'level', 'rank', 'Severity']),
                'File': self._get_file_path(item),
                'Line': self._get_field_value(item, ['line', 'beginline', 'start_line', 'lineNumber']),
                'Column': self._get_field_value(item, ['column', 'begincolumn', 'start_column', 'col']),
                'Message': self._get_message(item),
                'Rule': self._get_field_value(item, ['rule', 'check_id', 'rule_id', 'type', 'ruleId']),
                'Category': self._get_field_value(item, ['category', 'ruleset', 'impact'])
            }
            
            # Handle nested structures for different tools
            if 'start' in item and isinstance(item['start'], dict):
                violation['Line'] = item['start'].get('line', violation['Line'])
                violation['Column'] = item['start'].get('col', violation['Column'])
            
            # Handle PMD-style file structure
            if 'filename' in item and 'violations' in item:
                filename = item['filename']
                for sub_violation in item['violations']:
                    sub_v = violation.copy()
                    sub_v['File'] = filename
                    sub_v['Line'] = sub_violation.get('beginline', '')
                    sub_v['Column'] = sub_violation.get('begincolumn', '')
                    sub_v['Message'] = sub_violation.get('description', '')
                    sub_v['Rule'] = sub_violation.get('rule', '')
                    sub_v['Severity'] = f"Priority {sub_violation.get('priority', 'Unknown')}"
                    violations.append(sub_v)
            else:
                violations.append(violation)
                
        elif isinstance(item, list):
            for sub_item in item:
                violations.extend(self._process_violation_item(tool_name, sub_item, context))
        
        return violations
    
    def _get_field_value(self, item, possible_fields):
        """Get value from multiple possible field names"""
        for field in possible_fields:
            if field in item:
                value = item[field]
                # Handle nested text objects
                if isinstance(value, dict) and '#text' in value:
                    return str(value['#text'])
                return str(value)
        return ''
    
    def _get_file_path(self, item):
        """Extract file path from various possible locations"""
        file_fields = ['file', 'filename', 'path', 'sourcepath', 'target', 'Target']
        
        for field in file_fields:
            if field in item:
                return str(item[field])
        
        # Check for nested SourceLine
        if 'SourceLine' in item:
            source_line = item['SourceLine']
            if isinstance(source_line, list):
                source_line = source_line[0] if source_line else {}
            if isinstance(source_line, dict):
                return source_line.get('sourcepath', '')
        
        return ''
    
    def _get_message(self, item):
        """Extract message/description from various possible locations"""
        message_fields = ['message', 'description', 'title', 'summary', 'text']
        
        for field in message_fields:
            if field in item:
                value = item[field]
                if isinstance(value, dict) and '#text' in value:
                    return str(value['#text'])
                return str(value)
        
        # Check nested extra
        if 'extra' in item and isinstance(item['extra'], dict):
            for field in message_fields:
                if field in item['extra']:
                    return str(item['extra'][field])
        
        # Check nested LongMessage
        if 'LongMessage' in item:
            msg = item['LongMessage']
            if isinstance(msg, dict) and '#text' in msg:
                return str(msg['#text'])
            return str(msg)
        
        return 'No description available'
    
    def _extract_text_violations(self, tool_name, section_text):
        """Extract violations from text format (like Checkstyle warnings)"""
        violations = []
        
        # Pattern for Checkstyle-style warnings
        warning_pattern = r'\[(WARN|ERROR|INFO)\]\s+(.+?):(\d+):(\d+):\s+(.+?)\s+\[(.+?)\]'
        matches = re.findall(warning_pattern, section_text)
        
        for match in matches:
            level, file_path, line, column, message, rule = match
            violations.append({
                'Tool': tool_name,
                'Severity': level,
                'File': file_path,
                'Line': line,
                'Column': column,
                'Message': message,
                'Rule': rule,
                'Category': ''
            })
        
        return violations
    
    def create_comprehensive_reports(self):
        """Create all output formats"""
        if not self.processed_data:
            print("❌ No data to process")
            return
        
        # Create output directories
        output_dir = Path('dynamic_results')
        output_dir.mkdir(exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create DataFrame
        df = pd.DataFrame(self.processed_data)
        
        # Generate reports
        self._create_excel_report(df, output_dir, timestamp)
        self._create_html_report(df, output_dir, timestamp)
        self._create_text_summary(df, output_dir, timestamp)
        self._create_visualizations(df, output_dir, timestamp)
        
        print(f"\n🎉 All reports generated in '{output_dir}' directory!")
        print(f"📊 Total violations: {len(self.processed_data)}")
        print(f"🔧 Tools processed: {len(self.tools_data)}")
        for tool, data in self.tools_data.items():
            if data:  # Only show tools with data
                print(f"   - {tool}: {len(data)} violations")
    
    def _create_excel_report(self, df, output_dir, timestamp):
        """Create Excel report with separate sheets per tool"""
        excel_file = output_dir / f"dynamic_analysis_{timestamp}.xlsx"
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Overview sheet
            overview_data = []
            for tool, data in self.tools_data.items():
                if data:  # Only include tools with data
                    overview_data.append({
                        'Tool': tool,
                        'Total_Issues': len(data),
                        'Files_Affected': len(set(item['File'] for item in data if item['File'])),
                        'Severity_Breakdown': ', '.join([f"{sev}: {count}" for sev, count in 
                                                       pd.Series([item['Severity'] for item in data]).value_counts().items()])
                    })
            
            if overview_data:
                pd.DataFrame(overview_data).to_excel(writer, sheet_name='Overview', index=False)
            
            # Individual tool sheets
            for tool, data in self.tools_data.items():
                if data:  # Only create sheets for tools with data
                    tool_df = pd.DataFrame(data)
                    sheet_name = tool[:31]  # Excel sheet name limit
                    tool_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"📊 Excel report: {excel_file}")
    
    def _create_html_report(self, df, output_dir, timestamp):
        """Create comprehensive HTML report"""
        html_file = output_dir / f"dynamic_report_{timestamp}.html"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dynamic Analysis Results Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .severity-high {{ background-color: #ffebee; }}
        .severity-medium {{ background-color: #fff3e0; }}
        .severity-low {{ background-color: #f1f8e9; }}
        .tool-section {{ margin: 30px 0; }}
        .summary {{ background-color: #e3f2fd; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🔍 Dynamic Analysis Results Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>📋 Summary</h2>
        <p><strong>Total Violations:</strong> {len(self.processed_data)}</p>
        <p><strong>Tools Processed:</strong> {len([t for t, d in self.tools_data.items() if d])}</p>
        <p><strong>Files Affected:</strong> {len(set(item['File'] for item in self.processed_data if item['File']))}</p>
    </div>
"""
        
        # Add tool-specific sections
        for tool, data in self.tools_data.items():
            if data:  # Only include tools with data
                html_content += f"""
    <div class="tool-section">
        <h2>🔧 {tool} ({len(data)} violations)</h2>
        {pd.DataFrame(data).to_html(escape=False, classes='table table-striped')}
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🌐 HTML report: {html_file}")
    
    def _create_text_summary(self, df, output_dir, timestamp):
        """Create formatted text summary"""
        text_file = output_dir / f"summary_{timestamp}.txt"
        
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("🔍 DYNAMIC ANALYSIS RESULTS SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Violations: {len(self.processed_data)}\n")
            f.write(f"Tools Processed: {len([t for t, d in self.tools_data.items() if d])}\n\n")
            
            for tool, data in self.tools_data.items():
                if data:  # Only include tools with data
                    f.write(f"🔧 {tool}\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Total Issues: {len(data)}\n")
                    
                    # Severity breakdown
                    severities = [item['Severity'] for item in data if item['Severity']]
                    if severities:
                        severity_counts = pd.Series(severities).value_counts()
                        f.write("Severity Breakdown:\n")
                        for severity, count in severity_counts.items():
                            f.write(f"  - {severity}: {count}\n")
                    
                    # Top files
                    files = [item['File'] for item in data if item['File']]
                    if files:
                        file_counts = pd.Series(files).value_counts().head(5)
                        f.write("Top Affected Files:\n")
                        for file, count in file_counts.items():
                            f.write(f"  - {file}: {count} issues\n")
                    
                    f.write("\n")
        
        print(f"📄 Text summary: {text_file}")
    
    def _create_visualizations(self, df, output_dir, timestamp):
        """Create visualization charts"""
        if df.empty:
            return
        
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('🔍 Dynamic Analysis Results Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Tool distribution
        tool_counts = df['Tool'].value_counts()
        axes[0, 0].pie(tool_counts.values, labels=tool_counts.index, autopct='%1.1f%%')
        axes[0, 0].set_title('Distribution by Tool')
        
        # 2. Severity distribution
        severity_counts = df['Severity'].value_counts()
        axes[0, 1].bar(range(len(severity_counts)), severity_counts.values)
        axes[0, 1].set_xticks(range(len(severity_counts)))
        axes[0, 1].set_xticklabels(severity_counts.index, rotation=45)
        axes[0, 1].set_title('Distribution by Severity')
        
        # 3. Top affected files
        file_counts = df['File'].value_counts().head(10)
        if not file_counts.empty:
            axes[1, 0].barh(range(len(file_counts)), file_counts.values)
            axes[1, 0].set_yticks(range(len(file_counts)))
            axes[1, 0].set_yticklabels([f.split('/')[-1][:30] for f in file_counts.index])
            axes[1, 0].set_title('Top 10 Affected Files')
        
        # 4. Tool vs Severity heatmap
        if len(df) > 0:
            pivot_table = df.groupby(['Tool', 'Severity']).size().unstack(fill_value=0)
            if not pivot_table.empty:
                sns.heatmap(pivot_table, annot=True, fmt='d', cmap='YlOrRd', ax=axes[1, 1])
                axes[1, 1].set_title('Tool vs Severity Heatmap')
        
        plt.tight_layout()
        chart_file = output_dir / f"dashboard_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📈 Dashboard: {chart_file}")

def main():
    print("🚀 Starting Dynamic Analysis Processing...")
    
    processor = DynamicAnalysisProcessor()
    
    # Extract data from all tools
    processor.extract_tool_data()
    
    # Create comprehensive reports
    processor.create_comprehensive_reports()
    
    print("\n✅ Dynamic processing complete!")

if __name__ == "__main__":
    main()
