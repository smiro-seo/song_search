
import time, os, openai
from .const import default_img_format,aspect_ratios
import requests
from PIL import Image
import io, base64
import requests
local=True

cwd = os.path.dirname(__file__)
output_dir = os.path.join(cwd, '..', '..', '..', '..', 'var', 'song_search', 'feat_images') if not local else os.path.join(cwd,'feat_images')

image_prompt_ex_1=""
image_prompt_ex_2=""

gpt_max_tokens = 300
openai.api_key = ""
sleep_time_openai = 15  # seconds
default_gpt_options = {}
improver_prompt_options = {
    'temperature':0.75,
    'top_p': 1,
    'frequency_penalty':1,
    'presence_penalty':1
}
summarization_prompt_options = {}
image_prompt_options = {}

default_sd_options={'steps':30, 'style_preset':'photographic', 'aspect_ratio':'1:1'}
'''
    steps=50, # Amount of inference steps performed on image generation. Defaults to 30.
    cfg_scale=8.0, # Influences how strongly your generation is guided to match your prompt.
                # Setting this value higher increases the strength in which it tries to match your prompt.
                # Defaults to 7.0 if not specified.
    width=1024, # Generation width, if not included defaults to 512 or 1024 depending on the engine.
    height=1024, # Generation height, if not included defaults to 512 or 1024 depending on the engine.
    samples=1, # Number of images to generate, defaults to 1 if not included.
    sampler=generation.SAMPLER_K_DPMPP_2M # Choose which sampler we want to denoise our generation with.
                                                # Defaults to k_dpmpp_2m if not specified. Clip Guidance only supports ancestral samplers.
                                                # (Available Samplers: ddim, plms, k_euler, k_euler_ancestral, k_heun, k_dpm_2, k_dpm_2_ancestral, k_dpmpp_2s_ancestral, k_lms, k_dpmpp_2m, k_dpmpp_sde)
'''  

def get_gpt_response(prompt, engine, options=default_gpt_options):

    print("==============", engine)
    try:
        if 'davinci' in engine:
            # Davinci engines need Completion API
            completion= openai.Completion.create(
                engine=engine,
                max_tokens=gpt_max_tokens,
                prompt=prompt,
                n=1,
                **options
            )
            choice_response_text = completion['choices'][0].text.strip()
            choice_response_text = completion['choices'][0].text.strip().replace('"', '')
        else:
            # Every other engine (GPTs) need ChatCompletion API
            completion= openai.ChatCompletion.create(
                model=engine,
                max_tokens=gpt_max_tokens,
                messages=[{"role": "assistant", "content": prompt}],
                n=1,
                **options
            )
        
            choice_response_text = completion['choices'][0]['message']['content'].strip().replace('"', '')
        
        # Required timeout for OpenAI API
        print(f"Sleeping for {str(sleep_time_openai)} seconds")
        time.sleep(sleep_time_openai)

        return choice_response_text


    except Exception as e:
        print("ERROR IN CHATGPT")
        print(e)
        return ""

def get_stablediff_response(prompt, negative_prompt, keys, options=default_sd_options, filename=None):
    
    seed=None
    del options['steps']
    print(options)
    answer = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {keys['sd_key']}"
        },
        files={"none": ''},
        data={
            "prompt":prompt,
            #'samples':1,
            'style_preset':'photographic',
            **options
        },
    )
    answer = answer.json()

    try:
        if filename is None: filename = f'{str(answer["seed"])}.{default_img_format}'
        elif filename[-3:] != default_img_format: filename = filename + '.' + default_img_format
        filepath =  os.path.join(output_dir,filename)
        seed = answer['seed']

    except Exception as e:
        print("ERROR IN STABLE DIFF")
        print(e)
        return None, None, None
    # Get binary data from response and save to file
    img = Image.open(io.BytesIO(base64.b64decode(answer['image'])))

    
    #img = Image.open(io.BytesIO(data))
    img.save(filepath, optimize=True, quality=85) 

    with open(filepath, 'rb') as f:
        # Need to do this in order to get optimized image binary
        opt_data = f.read()
    
    return opt_data, filename, seed
    
def build_prompt(original_prompt, values_to_replace):
    # Builds prompt based on placeholder text such as [Artist]

    prompt = original_prompt.lower()
    for placeholder, value in values_to_replace.items():
        prompt = prompt.replace(placeholder, value)
    prompt = prompt.capitalize()

    return prompt


class Model_Generator():
    def __init__(self, search, keys):
        #Creates a generator based on search data and keys
        openai.api_key = keys['openai_key']
        self.sd_key = keys['sd_key']
        self.search = search
    
    def song_description(self, data, stopper):

        if (stopper.is_set()): raise Exception("stopped")
        
        # Build prompt
        values_to_replace = {
            '[track name]':data['track_name'],
            '[artist]':data['artist'],
            '[release year]': data['release_year']
        } | self.search.values_to_replace
        prompt = build_prompt(self.search.prompt, values_to_replace)

        # Get response
        response = get_gpt_response(prompt, self.search.model)

        # Improve if necessary 
        if self.search.improve_song: response = self.improve(response)

        return response
    
    def intro(self):
    
        print("Getting OpenAI introduction")


        response = get_gpt_response(self.search.intro_prompt, self.search.model)
        
        if self.search.improve_intro: response = self.improve(response)

        return response

    def improve(self, old_text):
        print("Improving openAI response.")

        if '[old text]' in self.search.improver_prompt:
            prompt = self.search.improver_prompt.replace('[old text]', old_text)
        else:
            prompt = self.search.improver_prompt + '\n\n' + old_text

        return get_gpt_response(prompt, 'gpt-4o', options=improver_prompt_options)

    def feat_image(self, filename=None):

        # Generate article summary through GPT
        print("Generating article summary")
        print(self.search)
        summ_prompt = f"Summarize the following article about {self.search.wp_title}:\n\n"
        summ_prompt = summ_prompt + self.search.full_text


        summ_response = get_gpt_response(summ_prompt, 'gpt-4o', options=summarization_prompt_options)

        # Add summary to user-inputted image prompt
        sd_text_prompt = self.search.img_prompt
        if "[summary]" in self.search.img_prompt:
            sd_text_prompt = sd_text_prompt.replace('[summary]', summ_response) + "\n\nOnly reply with the prompt, do not add any text besides that"
        else:
            sd_text_prompt = sd_text_prompt + "\n\nOnly reply with the prompt, do not add any text besides that. Summarized article:\n" + summ_response
        
        sd_prompt = get_gpt_response(sd_text_prompt, 'gpt-4o', options=image_prompt_options)

        # Add positive and negative keywords to prompt
        sd_prompt = sd_prompt + " " + ", ".join(self.search.image_prompt_keywords)
        sd_negative_prompt = 'painting, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, deformed, ugly, blurry, bad anatomy, bad proportions, extra limbs, cloned face, skinny, glitchy, double torso, extra arms, extra hands, mangled fingers, missing lips, ugly face, distorted face, extra legs, anime'
        sd_negative_prompt += ", " + ", ".join(self.search.image_nprompt_keywords)

        # Get stability options
        options=self.search.img_config
        
        options['aspect_ratio']= options.get('aspect-ratio', '1:1')
        del options['aspect-ratio']

        bin_file, filename, seed = get_stablediff_response(sd_prompt, sd_negative_prompt, self.search.keys, filename=filename, options=options)

        return bin_file, filename, sd_prompt, seed
