# Downscaling Models

This directory includes source code for the various statistical downscaling models and tools developed by graduate students at the Facility for Intelligent Decision Support. These models include weather generators, change factor climate scaling algorithms, and regression based models. In addition, a user interface has also been developed to facilitate the preparation of data files to be used in each model. Each sub-directory here includes one of the downscaling models or tools listed below, along with sample input and output CSV files, and instructions on running the models.

For more detailed instructions and information regarding these models, please refer to our bluebook available [here](http://www.eng.uwo.ca/research/iclr/fids/publications/products/97.pdf). If you wish to use the models for reasearch or publication purposes, please cite our bluebook as:

>Sohom Mandal, Patrick A. Breach, Abhishek Gaur and Slobodan P. Simonovic (2016). Tools for Downscaling Climate Variables: A   Technical Manual. Water Resources Research Report no. 097, Facility for Intelligent Decision Support, Department of Civil and Environmental Engineering, London, Ontario, Canada, 95 pages. ISBN: (print) 978-0-7714-3135-7; (online) 978-0-7714-3136-4.

| Model | Directory | Language
| ------ | ------ | ------ |
| Beta Regression (BR) |downscaling/br | Matlab | 
| Change Factor Methodology (CFM) | downscaling/cfm | Python |
| Inverse Distance Weighted Interpolation (IDW) | downscaling/idw | Python |
| K-Nearest Neighbor Weather Generator (KNN-CAD) | downscaling/knncad | Python|
| Maximum Entropy Bootstrap Weather Generator (MBEWG) | downscaling/mbewg | Matlab |
| Physical Scaling Model (SP) | downscaling/sp | R |

The interface used to prepare data inputs is located in downscaling/ui.
