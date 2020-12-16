from flask import request, render_template_string
import pathlib
from io import StringIO
import datetime

from fHDHR.tools import humanized_time


class Origin_HTML():
    endpoints = ["/origin", "/origin.html"]
    endpoint_name = "page_origin_html"

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

        self.template_file = pathlib.Path(self.fhdhr.config.internal["paths"]["origin_web"]).joinpath('origin.html')
        self.template = StringIO()
        self.template.write(open(self.template_file).read())

    def __call__(self, *args):
        return self.get(*args)

    def get(self, *args):

        if self.fhdhr.originwrapper.setup_success:
            origin_status_dict = {"Setup": "Success"}
        else:
            origin_status_dict = {"Setup": "Failed"}

        origin_status_dict["Temp"] = self.fhdhr.originwrapper.get_ceton_getvar(0, "Temperature")

        for i in range(int(self.fhdhr.config.dict["fhdhr"]["tuner_count"])):
            origin_status_dict["Tuner"+str(i)] = {}
            origin_status_dict["Tuner"+str(i)]['State'] = self.fhdhr.originwrapper.get_ceton_getvar(i, "TransportState")
            origin_status_dict["Tuner"+str(i)]['Signal'] = self.fhdhr.originwrapper.get_ceton_getvar(i, "Signal_Level")
            origin_status_dict["Tuner"+str(i)]['SNR'] = self.fhdhr.originwrapper.get_ceton_getvar(i, "Signal_SNR")
        return render_template_string(self.template.getvalue(), request=request, fhdhr=self.fhdhr, origin_status_dict=origin_status_dict, list=list)
