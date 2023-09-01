from numpy import result_type
import supplementary as s

def rendering_for_one_person(object_emotion_inanimate,rendering,preprocessors,person_count,res):
    caption = 0
    celeb = object_emotion_inanimate[0]["celebrity"]["name"]
    if(celeb != "None"):
        caption +=1
        rendering = "Image possibly contains: "
        if(person_count>1):
            rendering = "Image possibly contains: " + str(person_count) +" people with one of them being "
        emotion = " "
        if(object_emotion_inanimate[0]["emotion"]["emotion"] != "None"):
            emotion = object_emotion_inanimate[0]["emotion"]["emotion"]
            if("happy"in emotion or "sad" in emotion):
                emotion = emotion + " "
            else:
                emotion = " a neutral faced "
            emotion_flag = True
        rendering = rendering + emotion + celeb 
    else:
        caption += 1
        rendering = "Image possibly contains: "
        gender = " person "
        emotion = " "
        if(object_emotion_inanimate[0]["emotion"]["emotion"] != "None"):
            emotion = object_emotion_inanimate[0]["emotion"]["emotion"]
            if("happy"in emotion or "sad" in emotion):
                emotion = "a " + emotion  
            else:
                emotion = " a neutral"
            emotion += " faced "
            emotion_flag = True
        rendering += emotion + gender
    clothes = object_emotion_inanimate[0]["clothes"]
    cloth_flag = False
    emotion_flag= False
    if(clothes != "None"):
        # print("rendering before clothes process:", rendering)
        caption += 1
        cloth_flag=True
        cloth = ""
        for i in range(len(clothes)):
            if(clothes[i]["article"] != "None" and clothes[i]["confidence"]>=0.40):
                try:
                    if(clothes[i]["color"] is not None):
                        cloth += " " + clothes[i]["color"] + " "
                    cloth = cloth + clothes[i]["article"]
                except:
                    cloth = cloth + clothes[i]["article"]
            if(len(clothes)==1):
                cloth = cloth
       
            elif(i==(len(clothes)-2) and len(clothes)>1):
                cloth = cloth + " and "
            else:
                cloth = cloth + " , "
        if(len(cloth)>0 and cloth != " , "):
            rendering +=  " ,wearing: " + cloth + ". "
        else:
            rendering += ". "
        rendering = s.get_position(object_emotion_inanimate,person_count,rendering)
        rendering  = s.inanimate_rendering(object_emotion_inanimate[0]["inanimate"],rendering,res)
        emotion_flag = False
    segment = preprocessors["ca.mcgill.a11y.image.preprocessor.semanticSegmentation"]["segments"]
    for i in range(len(segment)):
        if("person" in segment[i]["name"]):
            area = segment[i]["area"]
            break
    return rendering, caption