// Which input annotation to use
input_class = "Tumor";
use_present = true;

// Content of each channel:
channel_1 = "Ki67";
channel_2 = "Nuclei";
channel_3 = "Caspase";
channel_4 = "HES1";

// LUT to use for a given channel (RGB):
LUTs = [
    "Ki67"   : [255, 0  , 0  ],
    "Nuclei" : [0  , 0  , 255],
    "Caspase": [0  , 255, 0  ],
    "HES1"   : [255, 255, 255]
];

// Segmentation settings (StarDist):
model_path = "/home/clement/Desktop/stardist-models/dsb2018_heavy_augment.pb";
expansion_distance = 5.0;

// ##################################################

import qupath.ext.stardist.StarDist2D
import qupath.lib.scripting.QP
import qupath.lib.objects.PathDetectionObject

// --- 1. Rename channels and update LUTs ---

setChannelNames(channel_1, channel_2, channel_3, channel_4);

colors = [];
nC = QP.getCurrentServer().nChannels();
for (i = 0 ; i < nC ; ++i) {
    c_name = QP.getCurrentServer().getChannel(i).getName();
    c_rgb = LUTs[c_name];
    int rgb = c_rgb[0];
    rgb = (rgb << 8) + c_rgb[1];
    rgb = (rgb << 8) + c_rgb[2];
    colors << rgb;
}

QP.setChannelColors(*colors);

// --- 2. Run StarDist on the 'Nuclei' channel ---

if (use_present) {
    QP.deselectAll();
    QP.selectObjectsByClassification(input_class);
} else {
    QP.selectObjectsByClassification(input_class);
    QP.removeSelectedObjects();
    QP.createFullImageAnnotation(true);
    QP.classifySelected(input_class);
    QP.getSelectedObjects()[0].setLocked(true);
}

stardist = StarDist2D
    .builder(model_path)
    .channels('Nuclei')                // Extract channel called 'DAPI'
    .normalizePercentiles(0.05, 99.95) // Percentile normalization
    .threshold(0.5)                    // Probability (detection) threshold
    .pixelSize(0.325)                  // Resolution for detection
    .cellExpansion(expansion_distance) // Expand nuclei to approximate cell boundaries
    .measureShape()                    // Add shape measurements
    .measureIntensity()                // Add cell measurements (in all compartments)
    .build();

pathObjects = QP.getSelectedObjects();
imageData = QP.getCurrentImageData();
stardist.detectObjects(imageData, pathObjects);
stardist.close(); // This can help clean up & regain memory
println('Segmentation done.');
