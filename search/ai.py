
import time, os, openai
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

cwd = os.path.dirname(__file__)
output_dir = os.path.join(cwd, '..', 'sd_app', 'model_outputs', 'feat_images')

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

default_sd_options={}
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

    try:
        if 'davinci' in engine:
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
            completion= openai.ChatCompletion.create(
                model=engine,
                max_tokens=gpt_max_tokens,
                messages=[{"role": "assistant", "content": prompt}],
                n=1,
                **options
            )
                                                        
            choice_response_text = completion['choices'][0]['message']['content'].strip().replace('"', '')
        

        print(f"Sleeping for {str(sleep_time_openai)} seconds")
        time.sleep(sleep_time_openai)

        return choice_response_text


    except Exception as e:
        print("ERROR IN CHATGPT")
        print(e)
        return ""

def get_stablediff_response(prompt, negative_prompt, keys, options=default_sd_options, filename=None):
    # Set up our connection to the API.
    stability = client.StabilityInference(
        key=keys['sd_key'], # API Key reference.
        verbose=True, # Print debug messages.
        engine="stable-diffusion-xl-1024-v0-9", # Set the engine to use for generation.
        # Available engines: stable-diffusion-xl-1024-v0-9 stable-diffusion-v1 stable-diffusion-v1-5 stable-diffusion-512-v2-0 stable-diffusion-768-v2-0
        # stable-diffusion-512-v2-1 stable-diffusion-768-v2-1 stable-diffusion-xl-beta-v2-2-2 stable-inpainting-v1-0 stable-inpainting-512-v2-0
    )

    # Set up our initial generation parameters.
    answers = stability.generate(
        prompt=prompt,
        width=512, # Generation width, if not included defaults to 512 or 1024 depending on the engine.
        height=512, # Generation height, if not included defaults to 512 or 1024 depending on the engine.
        samples=1, # Number of images to generate, defaults to 1 if not included.
        **options
    )

    # Set up our warning to print to the console if the adult content classifier is tripped.
    # If adult content classifier is not tripped, save generated images.
    
    for resp in answers:
        for response in resp.artifacts:

            if response.type == generation.ARTIFACT_IMAGE:
                if filename is None: filename = str(response.seed) + '.png'
                elif filename[-4:] != '.png': filename = filename + '.png'
                filepath =  os.path.join(output_dir,filename)

                with open(filepath, 'wb') as img:
                    img.write(response.binary)
                return response.binary, filename
    
def build_prompt(original_prompt, values_to_replace):
    
    prompt = original_prompt.lower()
    for placeholder, value in values_to_replace.items():
        prompt = prompt.replace(placeholder, value)
    prompt = prompt.capitalize()

    return prompt


class Model_Generator():
    def __init__(self, search, keys):

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
        print("prompt: " + self.search.intro_prompt)

        response = get_gpt_response(self.search.intro_prompt, self.search.model)
        
        if self.search.improve_intro: response = self.improve(response)

        return response

    def improve(self, old_text):
        print("Improving openAI response.")

        if '[old text]' in self.search.improver_prompt:
            prompt = self.search.improver_prompt.replace('[old text]', old_text)
        else:
            prompt = self.search.improver_prompt + '\n\n' + old_text

        return get_gpt_response(prompt, 'gpt-3.5-turbo', options=improver_prompt_options)

    def feat_image(self):

        print("Generating article summary")
        summ_prompt = f"Summarize the following article about {self.search.wp_title}:\n\n"
        summ_prompt = summ_prompt + self.search.full_text

        summ_response = get_gpt_response(summ_prompt, 'gpt-3.5-turbo', options=summarization_prompt_options)

        sd_text_prompt = self.search.img_prompt
        if "[summary]" in self.search.img_prompt:
            sd_text_prompt = sd_text_prompt.replace('[summary]', summ_response) + "\n\nOnly reply with the prompt, do not add any text besides that"
        else:
            sd_text_prompt = sd_text_prompt + "\n\nOnly reply with the prompt, do not add any text besides that. Summarized article:\n" + summ_response
        
        sd_prompt = get_gpt_response(sd_text_prompt, 'gpt-3.5-turbo', options=image_prompt_options)

        sd_prompt = sd_prompt + " " + ", ".join(self.search.image_prompt_keywords)
        sd_negative_prompt = 'codeugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, bad anatomy, watermark, signature, cut off, low contrast, underexposed, overexposed, bad art, beginner, amateur, distorted face'
        sd_negative_prompt += ", " + ", ".join(self.search.image_nprompt_keywords)

        print("Prompt for stable diffusion:")
        print(sd_prompt)
        print("Negative prompt:")
        print(sd_negative_prompt)

        return get_stablediff_response(sd_prompt, sd_negative_prompt, self.search.keys)