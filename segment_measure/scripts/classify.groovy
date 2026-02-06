classification_channels = ["Caspase", "Ki67"];

//###################################################################

// Probe available channels
available_channels = [];
for (i = 0 ; i < getCurrentServer().nChannels() ; ++i) {
    available_channels << getCurrentServer().getChannel(i).getName();
}

// We keep only the ones present in the image
classifiables = [];
for (channel: available_channels) {
    if (channel in classification_channels) {
        classifiables << channel;
    }
}

// Probe the list of object classifiers
available_classifiers = getProject().getObjectClassifiers().getNames();
classification_pool = [];

for (c: classifiables) {
    target_name = "find-" + c;
    if (target_name in available_classifiers) {
        classification_pool << target_name;
    }
}

println("Classifications: ")
for (clf: classification_pool) {
    println(" - Found: '" + clf + "'");
}

// Run the classification
runObjectClassifier(*classification_pool);
println("Classification done.");

