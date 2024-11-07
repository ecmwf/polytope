import eccovjson.decoder.BoundingBox
import eccovjson.decoder.Frame
import eccovjson.decoder.TimeSeries
import eccovjson.decoder.VerticalProfile
import eccovjson.encoder.BoundingBox
import eccovjson.encoder.Frame
import eccovjson.encoder.TimeSeries
import eccovjson.encoder.VerticalProfile

features_encoder = {
    "pointseries": eccovjson.encoder.TimeSeries.TimeSeries,
    "verticalprofile": eccovjson.encoder.VerticalProfile.VerticalProfile,
    "boundingbox": eccovjson.encoder.BoundingBox.BoundingBox,
    "frame": eccovjson.encoder.Frame.Frame,
}
features_decoder = {
    "pointseries": eccovjson.decoder.TimeSeries.TimeSeries,
    "verticalprofile": eccovjson.decoder.VerticalProfile.VerticalProfile,
    "boundingbox": eccovjson.decoder.BoundingBox.BoundingBox,
    "frame": eccovjson.decoder.Frame.Frame,
}


class Eccovjson:
    def __init__(self):
        pass

    def encode(self, type, domaintype):
        if domaintype == "timeseries":
            domaintype = "PointSeries"
        feature = self._feature_factory(domaintype.lower(), "encoder")
        return feature(type, domaintype)

    def decode(self, covjson):
        requesttype = covjson["domainType"]
        if requesttype == "timeseries":
            requesttype = "PointSeries"
        elif requesttype == "MultiPoint":
            requesttype = "boundingbox"
        feature = self._feature_factory(requesttype.lower(), "decoder")
        return feature(covjson)

    def _feature_factory(self, feature_type, encoder_decoder):
        if encoder_decoder == "encoder":
            features = features_encoder
        elif encoder_decoder == "decoder":
            features = features_decoder
        return features[feature_type]
