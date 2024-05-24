import codecs
import ast
from typing import Any, Dict

with codecs.open("23-11-05_1013.alog", "rb", encoding='utf-8') as alog:

    result: Dict[str, Any] = ast.literal_eval(alog.read())

    # print(result)
    print(result['timex'])
    print(result['temp1'])
    print(result['temp2'])
    print(result['extraname1'])
    print(result['extratemp1'][0])
