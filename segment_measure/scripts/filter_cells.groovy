import qupath.lib.objects.PathDetectionObject

/**
 * To remove false nuclei present in the background or in darker areas, we filter them by intensity of DAPI signal.
 * To be conserved as an actual nucleus, the mean intensity inside a nucleus must be superior to a certain threshold.
 * The threshold is processed by taking a percentage of the median intensity of all nuclei inside a given annotation (e.g. "Tumor").
 * The percentage can be adjusted below using the 'med_percentage' variable.
 * This is a percentage represented as a float in the range [0.0, 1.0] (e.g., 0.25 for 25%).
 */
med_percentage = 0.25; // in range [0.0, 1.0]

/**
 * Debris or small nuclei can also be filtered out by area.
 * Set the minimum and maximum area (in µm^2) below/above.
 */
min_area = 15.0; // µm^2
max_area = 190.0; // µm^2

/**
 * If true, objects that are too small, too large or have too low DAPI intensity will be deleted.
 * If false, they will just be classified as "Ignore*" and appear in gray in the viewer.
 */
delete_objects = false;

// #########################################################################################################

QP.deselectAll();
QP.selectObjectsByClassification("Tumor");

// --- 3+4. Mark objects that don't have enough DAPI signal or an incorrect size ---
property = "Nucleus: Nuclei: Median";
for (PathObject o: QP.getSelectedObjects()) {
    def cells = o.getChildObjects();
    def values = [];
    // Accumulate areas
    for (c: cells) {
        def m = c.getMeasurementList();
        def p = m.get(property);
        values << p;
        area = m.get("Nucleus: Area µm^2");
        if ((area < min_area) || (area > max_area)) {
            c.setClassification("Ignore*");
        } else {
            c.setClassification("");   
        }
    }
    // Sort areas and search for the top X%
    values.sort();
    
    mean = values.sum() / values.size();
    median = values[values.size() / 2];
    threshold_intensity = median * med_percentage;
    
    println("Median intensity: " + values[values.size() / 2].toString());
    println("Mean intensity: " + mean.toString());
    println("Threshold intensity: " + threshold_intensity.toString());
    
    for (c: cells) {
        def m = c.getMeasurementList();
        if (m.get(property) < threshold_intensity) {
            c.setClassification("Ignore*");
        }
    }
}

if (delete_objects) {
    QP.deselectAll();
    QP.selectObjectsByClassification("Ignore*");
    QP.removeSelectedObjects();
}

