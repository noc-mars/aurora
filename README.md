# Ocean data

This repository accompanies the dataset and the report "LEARNER, Auv Navigation and Multisensor Datafor Underwater Robotics", by Marco Bernardi, Brett Hosking, Chiara Petrioli, Brian J. Bett, Daniel Jones, Veerle Huvenne, Rachel Marlow, Maaten Furlong, Steve McPhail and Andrea Munafo.

> **Abstract** The current maturity of autonomous underwater vehicles (AUVs) has made their deployment practical and cost-effective, such that many scientific, industrial and military applications now include AUV operations. However, the logistical difficulties and high costs of operating at-sea are still critical limiting factors in further technology development, the benchmarking of new techniques and the reproducibility of research results. To overcome this problem, we present a freely available dataset suitable to test control, navigation, sensor processing algorithms and others tasks. This dataset combines AUV navigation data, side-scan sonar, multibeam echosounder data and seafloor camera image data, and associated sensor acquisition meta-data to provide a detailed characterisation of surveys carried out by the National Oceanography Centre (NOC) in the Greater Haig Fras Marine Conservazion Zone (MCZ) of the U.K in 2015.


<p align="center">
<img src="haig-fras.png" width="600" height=250>
</p>



## Packages and dependencies

Necessary packages:

```
conda install -c anaconda scipy
conda install -c conda-forge gdal
pip install opencv-python
pip install Pillow
```

To integrate it better with jupyter notebook run the following command:
```
python -m ipykernel install --user --name learner --display-name="learner"

```
You can now select the correct kernel directly from the Kernel menu.

If your jupyter_client in your environment is <5.3 then you might need to activate the ipyleaflet environment. You can do so, running:
```
jupyter nbextension enable --py --sys-prefix ipyleaflet
```

## Run it

Run the main notebook [ocean-data.ipynb](ocean-data.ipynb).
