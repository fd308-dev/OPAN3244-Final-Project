
#1 Create an Anaconda Virtual Environment:
```sh
conda create -n amazon-tracker python=3.11 -y
conda activate amazon-tracker

#2 Install dependencies:
pip install -r requirements.txt

#3 Run the code:
python PriceTracker/PriceTracker.py

Example URL:
https://www.amazon.co.uk/Goaycer-Bamboo-Toothbrushes-Medium-Toothbrush/dp/B08QRJRXT4/ref=sxin_15_pa_sp_search_thematic_sspa?content-id=amzn1.sym.bf628e5e-4d36-4c28-b465-d3cd4536d1ab%3Aamzn1.sym.bf628e5e-4d36-4c28-b465-d3cd4536d1ab&crid=2QI0YORM45NL8&cv_ct_cx=toothbrush&keywords=toothbrush&pd_rd_i=B08QRJRXT4&pd_rd_r=eb71573f-b628-421b-a89c-33b206b7b857&pd_rd_w=BWZ6Q&pd_rd_wg=9QaNF&pf_rd_p=bf628e5e-4d36-4c28-b465-d3cd4536d1ab&pf_rd_r=0MNDSKCF83AKHRB6WJA1&qid=1766006981&s=amazon-devices&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D&sprefix=toothbrush%2Camazon-devices%2C83&sr=1-3-fbc3951e-6c4e-4104-85d5-8dff376e781b-spons&aref=gbBobxgBHq&sp_csd=d2lkZ2V0TmFtZT1zcF9zZWFyY2hfdGhlbWF0aWM&psc=1

#4 Run tests:
pytest


