# Downscaling Models

This directory includes source code for the various statistical downscaling models and tools developed by graduate students at the Facility for Intelligent Decision Support. These models include weather generators, change factor climate scaling algorithms, and regression based models. In addition, a user interface has also been developed to facility the preparation of data files to be used in each model. Each sub-directory here includes one of the downscaling models or tools listed below, along with sample input and output CSV files, and instructions on running the models.

For more detailed instructuions and information regarding these models, please refer to our bluebook available here. If you wish to use the models for reasearch or publication purposes, please cite the bluebook.

| Model | Directory | Language
| ------ | ------ | ------ |
| Beta Regression (BR) |downscaling/br | Matlab | 
| Change Factor Methodology (CFM) | downscaling/cfm | Python |
| Inverse Distance Weighted Interpolation (IDW) | downscaling/idw | Python |
| K-Nearest Neighbor Weather Generator (KNN-CAD) | downscaling/knncad | Python|
| Maximum Entropy Bootstrap Weather Generator (MBEWG) | downscaling/mbewg | Matlab |

The interface used to prepare data inputs is located in downscaling/ui.
