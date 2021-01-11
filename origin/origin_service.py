import re
import time
from random import randint


class OriginService():

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

        count = int(self.fhdhr.config.dict["fhdhr"]["tuner_count"])
        for i in range(count):
            self.startstop_ceton_tuner(i, 0)

    def get_ceton_getvar(self, instance, query):
        query_type = {
                      "Frequency": "&s=tuner&v=Frequency",
                      "ProgramNumber": "&s=mux&v=ProgramNumber",
                      "CopyProtectionStatus": "&s=diag&v=CopyProtectionStatus",
                      "Temperature": "&s=diag&v=Temperature",
                      "Signal_Level": "&s=diag&v=Signal_Level",
                      "Signal_SNR": "&s=diag&v=Signal_SNR",
                      "TransportState": "&s=av&v=TransportState"
                     }

        getVarUrl = "http://%s/get_var?i=%s%s" % (self.fhdhr.config.dict["origin"]["ceton_ip"], instance, query_type[query])

        try:
            getVarUrlReq = self.fhdhr.web.session.get(getVarUrl)
            getVarUrlReq.raise_for_status()
        except self.fhdhr.web.exceptions.HTTPError as err:
            self.fhdhr.logger.error('Error while getting Ceton tuner variable for %s: %s' % (query, err))
            return None

        result = re.search('get.>(.*)</body', getVarUrlReq.text)

        return result.group(1)

    def get_ceton_tuner_status(self, chandict):
        found = 0
        count = int(self.fhdhr.config.dict["fhdhr"]["tuner_count"])
        for instance in range(count):

            result = self.get_ceton_getvar(instance, "TransportState")

            if result == "STOPPED":
                self.fhdhr.logger.info("Selected Ceton tuner#: %s" % instance)
                found = 1
                break

        return found, instance

    def startstop_ceton_tuner(self, instance, startstop):
        if not startstop:
            port = 0
            self.fhdhr.logger.info('Ceton tuner %s to be stopped' % instance)
        else:
            port = randint(41001, 49999)
            self.fhdhr.logger.info('Ceton tuner %s to be started' % instance)

        StartStopUrl = ("http://%s/stream_request.cgi" % self.fhdhr.config.dict["origin"]["ceton_ip"])

        StartStop_data = {"instance_id": instance,
                          "dest_ip": self.fhdhr.config.dict["fhdhr"]["address"],
                          "dest_port": port,
                          "protocol": 0,
                          "start": startstop}
        # StartStopUrl_headers = {
        #                    'Content-Type': 'application/json',
        #                    'User-Agent': "curl/7.64.1"}

        try:
            StartStopUrlReq = self.fhdhr.web.session.post(StartStopUrl, StartStop_data)
            StartStopUrlReq.raise_for_status()
        except self.fhdhr.web.exceptions.HTTPError as err:
            self.fhdhr.logger.error('Error while setting station stream: %s' % err)
            return None

        return port

    def set_ceton_tuner(self, chandict, instance):
        tuneChannelUrl = ("http://%s/channel_request.cgi" % self.fhdhr.config.dict["origin"]["ceton_ip"])
        tuneChannel_data = {"instance_id": instance,
                            "channel": chandict['number']}

        try:
            tuneChannelUrlReq = self.fhdhr.web.session.post(tuneChannelUrl, tuneChannel_data)
            tuneChannelUrlReq.raise_for_status()
        except self.fhdhr.web.exceptions.HTTPError as err:
            self.fhdhr.logger.error('Error while tuning station URL: %s' % err)
            return None

        return 1

    def tuner_watchdog(self, chandict, instance):
        killit = 0

        self.fhdhr.logger.info("Starting Ceton tuner watch dog on tuner#: %s" % instance)
        statusUrl = "http://%s:%s/api/tuners?method=status&tuner=%s" % (self.fhdhr.config.dict["fhdhr"]["address"], self.fhdhr.config.dict["fhdhr"]["port"], instance)

        while True:
            time.sleep(6)

            try:
                statusUrlReq = self.fhdhr.web.session.get(statusUrl)
                statusUrlReq.raise_for_status()
            except self.fhdhr.web.exceptions.HTTPError as err:
                self.fhdhr.logger.error('Error getting status on fHDHR tuner#: %s: %s' % (instance, err))

            tunerdict = statusUrlReq.json()

            if tunerdict["status"] == "Active":
                if tunerdict["channel"] == chandict["number"]:
                    continue
                else:
                    killit = 1
            else:
                killit = 1

            if killit:
                self.startstop_ceton_tuner(instance, 0)
                break
