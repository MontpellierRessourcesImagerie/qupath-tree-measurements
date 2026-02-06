import numpy as np
import pandas as pd
from pathlib import Path
from pprint import pprint

def as_key(alias, start, end):
    return f"{alias}: ({int(100.0 * start)}%-{int(100.0 * end)}%)"

class MeasuresTree(object):
    def __init__(self, measurables):
        self.measurables = measurables
        self.flat_list = self.get_flat_measurables()
        self.current = [0 for _ in range(len(self.flat_list))] # [index measurable] = index milestone for this measurable
        self.upper_bound = self.make_upper_bound() # [index measurable] = number of milestones for this measurable

    def next(self):
        rank = len(self.current) - 1
        while rank >= 0:
            self.current[rank] += 1
            if self.current[rank] < self.upper_bound[rank]:
                break
            else:
                self.current[rank] = 0
                rank -= 1
        return rank >= 0

    def as_properties(self):
        properties = []
        for level, rank in enumerate(self.current):
            _, name, column, ranges = self.flat_list[level]
            start_end = ranges[rank]
            properties.append((name, column, start_end))
        return properties

    def make_upper_bound(self):
        upper_bound = []
        for level, name, column, ranges in self.flat_list:
            upper_bound.append(len(ranges))
        return upper_bound

    def get_flat_measurables(self):
        flat_measurables = []
        for name, properties in self.measurables.items():
            column = properties['column']
            milestones = properties['milestones']
            level = properties['level']
            ranges = []
            start = 0.0
            for end in milestones + [1.0]:
                ranges.append((start, end))
                start = end
            flat_measurables.append((level, name, column, ranges))
        return sorted(flat_measurables, key=lambda x: (x[0], x[1]))

class CellsSignalAnalyzer(object):
    def __init__(self, data_path):
        # Path of the TSV produced by QuPath's "Export measurements" function
        self.data_path = Path(data_path)
        # Content of QuPath's TSV file as a pandas DataFrame
        self.data = pd.read_csv(self.data_path, sep="\t")
        # List of mono-classification found in the TSV, multi-classifications are dumped.
        self.classifications = set()
        # Filled by make_summary() with the summary statistics of the analysis, one row per image.
        self.summary_stats = pd.DataFrame()
        # List of columns on which we want to make statistics, including their alias in the output and the milestones to process the thresholds.
        self.measurables = {}
        # Dictionary of raw values for each measurable and each reference image.
        self.raw_values = {}
        # List of images that we are going to use to process the threshold intensities according to the milestones.
        self.references = set()
        # Intensity threshold for each milestone of each measurable, computed from the reference images.
        self.thresholds = {}

    def set_references(self, reference_images):
        all_images = set(self.data['Image'].unique())
        for ref in reference_images:
            if ref not in all_images:
                raise ValueError(f"Reference image '{ref}' not found in the data.")
            self.references.add(ref)

    def get_references(self):
        return list(self.references)

    def get_measurables(self):
        return self.measurables.copy()
    
    def add_measurable(self, name, column, milestones=[], level=0):
        if column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in the data.")
        ms = sorted([f for f in milestones if f > 0.0 and f < 1.0])
        self.measurables[name] = {
            'column': column,
            'milestones': ms,
            'level': level
        }
    
    def get_columns(self):
        return [i for i in self.data.columns.tolist() if i.startswith("Cell") or i.startswith("Nucleus")]
    
    def get_images(self):
        return self.data['Image'].unique().tolist()
    
    def detect_classifications(self):
        if 'Classification' not in self.data.columns:
            raise ValueError("No 'Classification' column found in the data.")
        self.classifications = set(self.data['Classification'].dropna().unique().tolist())
        self.classifications = set([c for c in self.classifications if (':' not in c)])

    def get_classifications(self):
        return list(self.classifications)
    
    def format_classification(self):
        for clf in self.classifications:
            self.data[clf] = 0
        for clf in self.classifications:
            self.data[clf] = 0
            self.data.loc[self.data['Classification'] == clf, clf] = 1
        self.data.drop(columns=['Classification'], inplace=True)

    def make_summary(self):
        self.summary_stats = pd.DataFrame()
        s1 = self.summarize_classifiables()
        s2 = self.summarize_measurables()
        merged = []
        for i in range(len(s1)):
            merged_row = {**s1[i], **s2[i]}
            merged.append(merged_row)
        
        self.summary_stats = pd.DataFrame(merged)

    def summarize_classifiables(self):
        rows = []
        for image in self.get_images():
            row = {'Image': image}
            for c in self.classifications:
                for name, properties in self.measurables.items():
                    # buffer = toutes les valeurs pour la colonne 'm' qui sont de l'image 'i' et la classe 'c'.
                    buffer = self.data.loc[(self.data['Image'] == image) & (self.data[c] == 1), properties['column']].dropna().values
                    row[f"Num {c}"] = len(buffer)
                    row[f"Mean: [{name}] ({c})"] = np.mean(buffer)
                    row[f"Median: [{name}] ({c})"] = np.median(buffer)
                    row[f"StdDev: [{name}] ({c})"] = np.std(buffer)
            for name, properties in self.measurables.items():
                clf_sum = self.data[list(self.classifications)].sum(axis=1)
                buffer = self.data.loc[(self.data['Image'] == image) & (clf_sum == 0), properties['column']].dropna().values
                row[f"Num ∅"] = len(buffer)
                row[f"Mean: [{name}] (∅)"] = np.mean(buffer)
                row[f"Median: [{name}] (∅)"] = np.median(buffer)
                row[f"StdDev: [{name}] (∅)"] = np.std(buffer)
            rows.append(row)
        return rows

    def summarize_measurables(self):
        rows = []
        self.raw_values = {}
        for image in self.get_images():
            mt = MeasuresTree(self.measurables)
            image_data = self.data.loc[self.data['Image'] == image]
            row = {}
            self.raw_values[image] = {}
            while True:
                properties = mt.as_properties()
                tsv_key = "[" + " ∩ ".join([as_key(name, start, end) for name, _, (start, end) in properties]) + "]"
                print(f"Processing: {tsv_key}...")
                filtered_data = image_data.copy()
                for name, column, (start, end) in properties:
                    low, high = self.thresholds[as_key(name, start, end)]
                    filtered_data = filtered_data.loc[(filtered_data[column] >= low) & (filtered_data[column] < high)]
                column = properties[0][1]
                row[f"Num {tsv_key}"] = len(filtered_data)
                row[f"Mean: {tsv_key}"] = np.mean(filtered_data[column].values)
                row[f"Median: {tsv_key}"] = np.median(filtered_data[column].values)
                row[f"StdDev: {tsv_key}"] = np.std(filtered_data[column].values)
                rows.append(row)
                self.raw_values[image][tsv_key] = filtered_data[column].values
                if not mt.next():
                    break
        return rows
    
    def raw_values_to_tsv(self, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for image, values_dict in self.raw_values.items():
            all_data = {}
            for tsv_key, values in values_dict.items():
                all_data[tsv_key] = pd.Series(values)
            df = pd.DataFrame(all_data)
            filename = f"{image}.tsv"
            output_path = output_dir / filename
            df.to_csv(output_path, sep="\t", index=False)

    def process_thresholds(self):
        for name, properties in self.measurables.items():
            column = properties['column']
            milestones = properties['milestones']
            buffer = []
            for ref in self.references:
                values = self.data.loc[self.data['Image'] == ref, column].dropna().values
                buffer.extend(values)
            buffer = np.sort(np.array(buffer))
            start = 0.0
            total = len(buffer)
            for end in milestones+[1.0]:
                key = as_key(name, start, end)
                i1 = int(start * total)
                i2 = int(end * total) - 1
                self.thresholds[key] = (buffer[i1], buffer[i2])
                start = end
        pprint(self.thresholds)

if __name__ == "__main__":
    # 1. Classification
    analyzer = CellsSignalAnalyzer("/home/clement/Documents/projects/2285-dbracquemond/pjt1/measurements.tsv")
    analyzer.detect_classifications()
    analyzer.format_classification()

    # 2. Measure intensities
    analyzer.add_measurable(
        "Ki67 Intensity", 
        "Cell: Ki67: Median", 
        milestones=[0.25, 0.5, 0.75],
        level=0
    )
    analyzer.add_measurable(
        "HES1 Intensity", 
        "Cell: HES1: Median", 
        milestones=[0.333, 0.666],
        level=1
    )

    # 3. Set reference images and initialize thresholds
    analyzer.set_references([
        "merged_channels.tif"
    ])
    analyzer.process_thresholds()
    
    # 4. Run and save to the disk
    analyzer.make_summary()
    analyzer.summary_stats.to_csv(
        "/home/clement/Documents/projects/2285-dbracquemond/pjt1/summary_output.tsv", 
        sep="\t", 
        index=False
    )
    analyzer.raw_values_to_tsv("/home/clement/Documents/projects/2285-dbracquemond/pjt1/raw_values")