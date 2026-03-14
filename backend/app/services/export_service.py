import csv
import io
import json

class ExportService:
    def generate_csv(self, x_data, y_data):
        """
        Creates a CSV file in memory.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['Time (t)', 'Value (y)'])

        for t, y in zip(x_data, y_data):
            writer.writerow([t, y])

        return output.getvalue()

    def generate_json(self, x_data, y_data, metadata):
        """
        Creates a complete JSON report.
        """
        export_dict = {
            "meta": metadata,
            "data": [
                {"t": t, "y": y} for t, y in zip(x_data, y_data)
            ]
        }
        return json.dumps(export_dict, indent=4)