from typing import List

from src.class_def import Class

def encode_class(class_ist : Class):
    return f"{class_ist.teacher},{class_ist.subject},{class_ist.classroom},{class_ist.hour},{class_ist.day}"

def encode_solution(class_list : List[Class]):
    return ";".join(list(map(encode_class, class_list)))
