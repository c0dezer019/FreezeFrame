import time
import torch
import nodes
import comfy.samplers
import comfy.sample
import comfy.utils
import comfy.model_management
import latent_preview
from .shared import PAUSE_STATE

# --- NODE 1: STANDARD PAUSABLE SAMPLER ---
class PSampler:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, ),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, ),
                "positive": ("CONDITIONING", ),
                "negative": ("CONDITIONING", ),
                "latent_image": ("LATENT", ),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "sample"
    CATEGORY = "sampling/FreezeFrame"

    def sample(self, model, seed, steps, cfg, sampler_name, scheduler, positive, negative, latent_image, denoise):
        latent_samples = latent_image["samples"]
        batch_inds = latent_image.get("batch_index") if "batch_index" in latent_image else None
        noise = comfy.sample.prepare_noise(latent_samples, seed, batch_inds)
        noise_mask = latent_image.get("noise_mask", None)
        preview_callback = latent_preview.prepare_callback(model, steps, latent_image)

        def intercept_callback(step, x0, x, total_steps):
            human_step = step + 1
            if preview_callback: preview_callback(step, x0, x, total_steps)

            if PAUSE_STATE.get("command") == "PAUSE":
                print(f"[P-Sampler] ⏸️ PAUSED at Step {human_step}. Waiting...")
                while PAUSE_STATE.get("command") == "PAUSE": 
                    time.sleep(0.1)
                print(f"[P-Sampler] ▶️ RESUMED.")

        try:
            samples = comfy.sample.sample(
                model, noise, steps, cfg, sampler_name, scheduler, 
                positive, negative, latent_samples,
                denoise=denoise, 
                disable_noise=False, 
                start_step=0, 
                last_step=None, 
                force_full_denoise=False, 
                noise_mask=noise_mask, 
                callback=intercept_callback, 
                seed=seed
            )
        except comfy.model_management.InterruptProcessingException:
            print("[P-Sampler] 🛑 System Interrupt. Aborting.")
            raise

        out = latent_image.copy()
        out['samples'] = samples
        return (out,)

# --- NODE 2: ADVANCED PAUSABLE SAMPLER ---
class PSamplerAdvanced:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "add_noise": (["enable", "disable"], ),
                "noise_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, ),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, ),
                "positive": ("CONDITIONING", ),
                "negative": ("CONDITIONING", ),
                "latent_image": ("LATENT", ),
                "start_at_step": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "end_at_step": ("INT", {"default": 10000, "min": 0, "max": 10000}),
                "return_with_leftover_noise": (["disable", "enable"], ),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "sample"
    CATEGORY = "sampling/FreezeFrame"

    def sample(self, model, add_noise, noise_seed, steps, cfg, sampler_name, scheduler, positive, negative, latent_image, start_at_step, end_at_step, return_with_leftover_noise):
        force_full_denoise = (return_with_leftover_noise == "disable")
        disable_noise = (add_noise == "disable")
        latent_samples = latent_image["samples"]
        
        if not disable_noise:
            batch_inds = latent_image.get("batch_index") if "batch_index" in latent_image else None
            noise = comfy.sample.prepare_noise(latent_samples, noise_seed, batch_inds)
        else:
            noise = torch.zeros(latent_samples.size(), dtype=latent_samples.dtype, layout=latent_samples.layout, device="cpu")

        noise_mask = latent_image.get("noise_mask", None)
        preview_callback = latent_preview.prepare_callback(model, steps, latent_image)

        def intercept_callback(step, x0, x, total_steps):
            human_step = step + 1
            if preview_callback: preview_callback(step, x0, x, total_steps)

            if PAUSE_STATE.get("command") == "PAUSE":
                print(f"[P-Sampler] ⏸️ PAUSED at Step {human_step}. Waiting...")
                while PAUSE_STATE.get("command") == "PAUSE": 
                    time.sleep(0.1)
                print(f"[P-Sampler] ▶️ RESUMED.")

        try:
            samples = comfy.sample.sample(
                model, noise, steps, cfg, sampler_name, scheduler, 
                positive, negative, latent_samples,
                disable_noise=disable_noise, 
                start_step=start_at_step, 
                last_step=end_at_step, 
                force_full_denoise=force_full_denoise, 
                noise_mask=noise_mask, 
                callback=intercept_callback, 
                seed=noise_seed
            )
        except comfy.model_management.InterruptProcessingException:
            print("[P-Sampler] 🛑 System Interrupt. Aborting.")
            raise

        out = latent_image.copy()
        out['samples'] = samples
        return (out,)

# --- NODE 3: CUSTOM PAUSABLE SAMPLER ---
class PSamplerCustom:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "add_noise": ("BOOLEAN", {"default": True, "label_on": "enable", "label_off": "disable"}),
                "noise_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                "positive": ("CONDITIONING", ),
                "negative": ("CONDITIONING", ),
                "sampler": ("SAMPLER", ),
                "sigmas": ("SIGMAS", ),
                "latent_image": ("LATENT", ),
            }
        }

    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("output", "denoised_output")
    FUNCTION = "sample"
    CATEGORY = "sampling/FreezeFrame"

    def sample(self, model, add_noise, noise_seed, cfg, positive, negative, sampler, sigmas, latent_image):
        # 1. Setup Latent & Fix Empty Channels
        latent = latent_image
        latent_samples = latent["samples"]
        latent = latent.copy()
        latent_samples = comfy.sample.fix_empty_latent_channels(model, latent_samples, latent.get("downscale_ratio_spacial", None))
        latent["samples"] = latent_samples

        # 2. Generate Noise
        if add_noise:
            batch_inds = latent.get("batch_index") if "batch_index" in latent else None
            noise = comfy.sample.prepare_noise(latent_samples, noise_seed, batch_inds)
        else:
            noise = torch.zeros(latent_samples.size(), dtype=latent_samples.dtype, layout=latent_samples.layout, device="cpu")

        noise_mask = latent.get("noise_mask", None)

        # 3. Callback with x0 capture
        x0_output = {}
        preview_callback = latent_preview.prepare_callback(model, sigmas.shape[-1] - 1, x0_output)

        def intercept_callback(step, x0, x, total_steps):
            human_step = step + 1
            if preview_callback: preview_callback(step, x0, x, total_steps)

            if PAUSE_STATE.get("command") == "PAUSE":
                print(f"[P-Sampler] ⏸️ PAUSED at Step {human_step}. Waiting...")
                while PAUSE_STATE.get("command") == "PAUSE": 
                    time.sleep(0.1)
                print(f"[P-Sampler] ▶️ RESUMED.")

        # 4. Execution
        try:
            disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
            samples = comfy.sample.sample_custom(
                model, noise, cfg, sampler, sigmas, 
                positive, negative, 
                latent_samples,
                noise_mask=noise_mask, 
                callback=intercept_callback, 
                disable_pbar=disable_pbar, 
                seed=noise_seed
            )
        except comfy.model_management.InterruptProcessingException:
            print("[P-Sampler] 🛑 System Interrupt. Aborting.")
            raise

        # 5. Output Processing (with x0 support)
        out = latent.copy()
        out.pop("downscale_ratio_spacial", None)
        out['samples'] = samples
        
        if "x0" in x0_output:
            x0_out = model.model.process_latent_out(x0_output["x0"].cpu())
            if hasattr(samples, "is_nested") and samples.is_nested:
                latent_shapes = [x.shape for x in samples.unbind()]
                x0_out = comfy.nested_tensor.NestedTensor(comfy.utils.unpack_latents(x0_out, latent_shapes))
            
            out_denoised = latent.copy()
            out_denoised["samples"] = x0_out
        else:
            out_denoised = out

        return (out, out_denoised)

# --- NODE 4: CUSTOM ADVANCED PAUSABLE SAMPLER ---
class PSamplerCustomAdvanced:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "noise": ("NOISE", ),
                "guider": ("GUIDER", ),
                "sampler": ("SAMPLER", ),
                "sigmas": ("SIGMAS", ),
                "latent_image": ("LATENT", ),
            }
        }

    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("output", "denoised_output")
    FUNCTION = "sample"
    CATEGORY = "sampling/FreezeFrame"

    def sample(self, noise, guider, sampler, sigmas, latent_image):
        # 1. Setup Latent & Fix Empty Channels
        latent = latent_image
        latent_samples = latent["samples"]
        latent = latent.copy()
        
        latent_samples = comfy.sample.fix_empty_latent_channels(
            guider.model_patcher, latent_samples, latent.get("downscale_ratio_spacial", None)
        )
        latent["samples"] = latent_samples

        noise_mask = latent.get("noise_mask", None)

        # 2. Setup Callback with x0 capture
        x0_output = {}
        preview_callback = latent_preview.prepare_callback(guider.model_patcher, sigmas.shape[-1] - 1, x0_output)

        def intercept_callback(step, x0, x, total_steps):
            human_step = step + 1
            if preview_callback: preview_callback(step, x0, x, total_steps)

            if PAUSE_STATE.get("command") == "PAUSE":
                print(f"[P-Sampler] ⏸️ PAUSED at Step {human_step}. Waiting...")
                while PAUSE_STATE.get("command") == "PAUSE": 
                    time.sleep(0.1)
                print(f"[P-Sampler] ▶️ RESUMED.")

        # 3. Execution
        try:
            noise_tensor = noise.generate_noise(latent)
            disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED

            samples = guider.sample(
                noise_tensor, 
                latent_samples, 
                sampler, 
                sigmas, 
                denoise_mask=noise_mask, 
                callback=intercept_callback, 
                disable_pbar=disable_pbar, 
                seed=noise.seed
            )
        except comfy.model_management.InterruptProcessingException:
            print("[P-Sampler] 🛑 System Interrupt. Aborting.")
            raise

        # 4. Output Processing
        samples = samples.to(comfy.model_management.intermediate_device())

        out = latent.copy()
        out.pop("downscale_ratio_spacial", None)
        out["samples"] = samples
        
        if "x0" in x0_output:
            x0_out = guider.model_patcher.model.process_latent_out(x0_output["x0"].cpu())
            if hasattr(samples, "is_nested") and samples.is_nested:
                latent_shapes = [x.shape for x in samples.unbind()]
                x0_out = comfy.nested_tensor.NestedTensor(comfy.utils.unpack_latents(x0_out, latent_shapes))
            
            out_denoised = latent.copy()
            out_denoised["samples"] = x0_out
        else:
            out_denoised = out

        return (out, out_denoised)
