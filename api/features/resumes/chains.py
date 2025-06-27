from modules.base_chains import BaseChain
from modules.utils import clean_yaml_parser


chain_instance = BaseChain(output_parser=clean_yaml_parser)
