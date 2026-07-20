from source import SourceReader, SourceStats
from s_compression import SourceCodec, CompressionResult, Codebook
from coding import ErrorCorrectingCode, EncodedBlock, DecodedBlock, CodingStats
from channel import Channel, TransmissionResult


class Simulator():
    
    def __init__(
        self, source: SourceReader,
        codec: SourceCodec,
        code: ErrorCorrectingCode,
        channel: Channel):

        self.source: SourceReader       = source
        self._source_stats: SourceStats = None
    

        self.compressor: SourceCodec              = codec
        self._codebook: Codebook                  = None
        self._compressor_stats: CompressionResult = None


        self.code = code
        self._encoded_block = None
        self._decoded_block = None

        self.channel        = channel
        self._trans_result  = None

    def run(self, input):
        self._source_stats = self.source.read(input)

        self._codebook = self.compressor.build_codebook(
            self._source_stats.probabilities
        )
        self._compressor_stats= self.compressor.encode(
            self._source_stats.symbols,
            self._codebook
        )

        #Encode
        self._encoded_block = self.code.encode(
            self._compressor_stats.bits
        )

        #Send that tru channel
        self._trans_result = self.channel.transmit(
            self._encoded_block.codeword_bits
        )

        #Decode
        self._decoded_block = self.code.decode(
            self._trans_result.received
        )