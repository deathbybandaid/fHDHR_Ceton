import xmltodict
import base64
import re
import threading


class OriginChannels():

    def __init__(self, fhdhr, origin):
        self.fhdhr = fhdhr
        self.origin = origin

    def get_channels(self):
        cleaned_channels = []
        url_headers = {'accept': 'application/xml;q=0.9, */*;q=0.8'}

        count_url = ('http://' + self.fhdhr.config.dict["origin"]["ceton_ip"] +
                     '/view_channel_map.cgi?page=1')

        try:
            countReq = self.fhdhr.web.session.get(count_url, headers=url_headers)
            countReq.raise_for_status()
        except self.fhdhr.web.exceptions.HTTPError as err:
            self.fhdhr.logger.error('Error while getting channel count: %s' % err)
            return []

        count = re.search('(?<=1 to 50 of )\w+', countReq.text)
        count = int(count.group(0))
        page = 0

        while True:
            stations_url = "http://%s/view_channel_map.cgi?page=%s&xml=1" % (self.fhdhr.config.dict["origin"]["ceton_ip"], page)

            try:
                stationsReq = self.fhdhr.web.session.get(stations_url, headers=url_headers)
                stationsReq.raise_for_status()
            except self.fhdhr.web.exceptions.HTTPError as err:
                self.fhdhr.logger.error('Error while getting stations: %s' % err)
                return []

            stationsRes = xmltodict.parse(stationsReq.content)

            for station_item in stationsRes['channels']['channel']:
               nameTmp = station_item["name"]
               nameTmp_bytes = nameTmp.encode('ascii')
               namebytes = base64.b64decode(nameTmp_bytes)
               name = namebytes.decode('ascii')
               clean_station_item = {
                                "name": name,
                                "callsign": name,
                                "number": station_item["number"],
                                "eia": station_item["eia"],
                                "id": station_item["sourceid"],
                                }

               cleaned_channels.append(clean_station_item)

            if (count > 1024):
                count -= 1024
                page = 21
                continue
            else:
                break

            if (count > 0):
                count -= 50
                page += 1
            else:
                break

        return cleaned_channels

    def get_channel_stream(self, chandict, stream_args):

        found, instance = self.origin.get_ceton_tuner_status(chandict)

        # 1 to start or 0 to stop
        if found:
            port = self.origin.startstop_ceton_tuner(instance, 1)
        else:
            port = None
            self.fhdhr.logger.error('No Ceton tuners available')

        if port:
            tuned = self.origin.set_ceton_tuner(chandict, instance)
            self.fhdhr.logger.info('Preparing Ceton tuner %s on port: %s' % (instance,port))
        else:
            tuned = None

        self.origin.get_ceton_getvar(instance, "Frequency")
        self.origin.get_ceton_getvar(instance, "ProgramNumber")
        self.origin.get_ceton_getvar(instance, "CopyProtectionStatus")

        if tuned:
            self.fhdhr.logger.info('Initiate streaming channel %s from Ceton tuner#: %s ' % (chandict['number'],instance))
            streamurl = "udp://127.0.0.1:%s" % port
        else:
            streamurl = None

        wd = threading.Thread(target=self.origin.tuner_watchdog, args=(chandict, instance))
        wd.start()

        stream_info = {"url": streamurl}

        return stream_info
