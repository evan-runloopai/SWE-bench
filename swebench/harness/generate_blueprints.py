from __future__ import annotations

import json

from argparse import ArgumentParser
from pathlib import Path

from swebench.harness.constants import (
    KEY_INSTANCE_ID,
)
from swebench.harness.test_spec import make_test_spec
from swebench.harness.utils import load_swebench_dataset

from runloop_api_client import Runloop

runloop_client = Runloop(
    # This is the default and can be omitted
    base_url="https://api.runloop.pro",
    bearer_token="ak_2wxfTwzaiuuQCjGTJtHtU",
)

# A simple script that mimics the run_evaluation.py script in the SWE-Bench repo
# However, this script outputs the blueprint creation requests for the necessary images in runloop
def main(
        dataset_name: str,
        split: str,
        instance_ids: list,        
    ):
    """
    Run evaluation harness for the given dataset and predictions.
    """
    dataset = load_swebench_dataset(dataset_name, split)    
    if instance_ids:
        dataset = [i for i in dataset if i[KEY_INSTANCE_ID] in instance_ids]
    
    # build environment images + run instances
    test_specs = list(map(make_test_spec, dataset))
    #  For each test spec we are going to get the docker file and set up scripts and combine it all into a single blueprint creation
    RL_OUTPUT_DIR = Path("./runloop_output")
    RL_OUTPUT_DIR.mkdir(exist_ok=True)
            
    # Now we make a file with this information as JSON
    instance_images = {
        test_spec.instance_id: {                
            "platform": test_spec.platform,
            "base_dockerfile": test_spec.base_dockerfile,            
            "env_image_name": test_spec.env_image_key,
            "env_dockerfile": test_spec.env_dockerfile,
            "setup_env_script": test_spec.setup_env_script,
            "instance_image_name": test_spec.instance_image_key,
            "instance_dockerfile": test_spec.instance_dockerfile,
            "instance_setup_script": test_spec.install_repo_script
        } for test_spec in test_specs
    }

    for instance_id, instance_image_data in instance_images.items():
        with open(RL_OUTPUT_DIR / f"{instance_id}.json", "w") as f:
            json.dump(instance_image_data, f, indent=4)
        with open(RL_OUTPUT_DIR / f"{instance_id}_compostite.json", "w") as f:
            composite_dockerfile = "FROM runloopdocker:TODOFIXTHIS"
            # Remove the first line of the base dockerfile as it is the FROM line
            composite_dockerfile += instance_image_data["base_dockerfile"].lstrip().split("\n", 1)[1]
            composite_dockerfile += instance_image_data["env_dockerfile"].lstrip().split("\n", 1)[1]
            composite_dockerfile += instance_image_data["instance_dockerfile"].lstrip().split("\n", 1)[1]
            blueprint_request = {
                "dockerfile": composite_dockerfile,
                "file_mounts": {
                    "setup_env.sh": instance_image_data["setup_env_script"],
                    "setup_repo.sh": instance_image_data["instance_setup_script"]
                }
            }
            f.write(json.dumps(blueprint_request, indent=4))
            
    existing_blueprints = runloop_client.blueprints.list(limit="300")
    bp_map = {bp.name: bp for bp in existing_blueprints.blueprints}

    for instance_id, instance_image_data in instance_images.items():
        if instance_id in bp_map:
            print(f"Blueprint {instance_id} already exists")
            continue
        with open(RL_OUTPUT_DIR / f"{instance_id}_compostite.json", "r") as f:
            blueprint_request = json.load(f)
            bp = runloop_client.blueprints.create(
                file_mounts=blueprint_request["file_mounts"],
                dockerfile=blueprint_request["dockerfile"],
                name=instance_id
            )
            # Wait for the blueprint to be created successfully
            print("Creating blueprint", instance_id, bp.id)
            while bp.status not in ["build_complete", "failed"]:
                bp = runloop_client.blueprints.retrieve(id=bp.id)
            print("Blueprint complete", instance_id, bp)
            if bp.status == "failed":
                print("Blueprint failed", instance_id, bp)
                raise Exception("Blueprint failed")            

            

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dataset_name", default="princeton-nlp/SWE-bench_Lite", type=str, help="Name of dataset or path to JSON file.")
    parser.add_argument("--split", type=str, default="test", help="Split of the dataset")
    parser.add_argument("--instance_ids", nargs="+", type=str, help="Instance IDs to run (space separated)")    
    args = parser.parse_args()

    main(**vars(args))
