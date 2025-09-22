import json, jsonlines
from tqdm import tqdm
from pprint import pprint

import ast, re
from copy import deepcopy
from random import shuffle, seed
from material_parser.material_parser_old import MaterialParser
from contextlib import nullcontext
GPTV='4o'
finalflag=""
GPT4O_OUTPUTFILE=f'Paperportions_GPT{GPTV}_raw_outputs_text_masked{finalflag}.jsonl'
POSTPROCESSED_FILE=f'Paperportions_GPT{GPTV}_postprocessed{finalflag}.jsonl'

flag_halluc_filter=False
if 'unmasked' in GPT4O_OUTPUTFILE: # unmasked file contains raw full text of the paper
    flag_halluc_filter=True
    GPT4O_OUTPUTFILE_MASKED=f'Paperportions_GPT{GPTV}_raw_outputs_text_masked{finalflag}.jsonl'


def halluc_filter(inputtext, rxn, mode='elements_target',elements=None):
    """
    returns entities that are hallucinated, False if NOT hallucinated
    NOTE: this requires the raw text from the paper, which is discarded due to copyright issues
    # returns True if all entities in a single rxn are present in the input text
    mode: 'string' where looks at match in string using "in"
        'partial string' looking for fuzzywuzzy partial string match # NOT IMPLETMENTED
        'elements' looking if all elements are "in" the text only for target. Target tends to be x 1-x so applying weak filter to filter out obvious ones
    """
    if elements is None:
        elements=[]
    if mode=='string':
        entities=[rxn['target']]+rxn['precursors']
    elif mode=='elements_target':
        # run materialparser to rxn['target'] and get elements

        # elements

        entities= elements
    elif mode=='precs_string_elements_target':
        # run materialparser to rxn['target'] and get elements

        # elements

        entities= elements + rxn['precursors']

    if isinstance(rxn['impurity_phase'],list): # list of strings -> impurity phases
        impurity_phases = [comp for comp in rxn['impurity_phase'][:] if not isinstance(comp,bool)]
        if all([isinstance(imp,str) for imp in rxn['impurity_phase']]):
            entities.extend(impurity_phases)
        
        # elif rxn['impurity_phase'] in [[False],[True][None]]: # for some reason [True], [False], [None] are outputs
        # elif rxn['impurity_phase'] in [[True]]:
        else:
            print("ERROR in halluc_filter", rxn['impurity_phase'])
            return True

    elif isinstance(rxn['impurity_phase'],str) and (rxn['impurity_phase']=='True' or rxn['impurity_phase']=='False' or 'ERROR' in rxn['impurity_phase']):
        pass
    else:
        print("ERROR in halluc_filter", rxn['impurity_phase'])
        return True

    #halluc filter
    if all([comp in inputtext for comp in entities]):
        return False
    else:
        return [comp for comp in entities if comp not in inputtext]



def parse_material_string(mat):
    mp = MaterialParser(pubchem_lookup=False)
    parsed = mp.parse_material_string(mat)
    return parsed

def parse_material_elements(mat):
    elements=[]
    mp = MaterialParser(pubchem_lookup=False)
    parsed = mp.parse_material_string(mat)
    for comp in parsed['composition']:
        elements.extend(list(comp['elements']))
    return list(set(elements))

def parse_RxnImpoutput(list1):
    """
    example output from GPT
    ["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | [Bi2(Mn,Fe)4O9 + δ, (Mn,Fe)2O3]"]
    ["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False"]
    ["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | [Bi2(Mn,Fe)4O9 + δ, (Mn,Fe)2O3]","Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False"]
    """
    # get the string of list convert to list
    spans=[]
    for srch in re.finditer(r'(?<=|)(?<= )(\[(?:.*?)\])',list1):
        spans.append({'span':srch.span(),'match':srch.group()})

    idx=-1
    list1copy=list1[:]
    impphases=[]
    for span in reversed(spans):
        idx+=1

        list1copy=list1copy[:span['span'][0]]+f'IMPPHASE{idx}IMPPHASE'+list1copy[span['span'][1]:]
        impphases.append({'idx':idx,'phase':ast.literal_eval(span['match'])})
    # print(impphases)
    
    # print(list1copy)

    list1copy = ast.literal_eval(list1copy)
    reactions = []
    for Rxnstring in list1copy:
        # first divide by ==
        precsprods = Rxnstring.split("==")
        if len(precsprods)!=2:
            print("Parsing error in == split", Rxnstring)
            return 0
        precs = precsprods[0].split("+") # list of precs
        precs = [prec.strip() for prec in precs]
        prods = precsprods[1].split("|")
        if len(prods)!=2:
            print("Parsing error in | split", Rxnstring)
            return 0
        target = prods[0].strip()
        impurity = prods[1]
        # print(impurity)
        if impurity==" False":
            impurity="False"
        elif impurity==" True":
            impurity="True"
        elif "IMPPHASE" in impurity:
            impurityidx = int(impurity.replace("IMPPHASE",""))
            for imp in impphases:
                if imp['idx']==impurityidx:
                    impurity=imp['phase']
                    # for some reason [True], [False], [None] are outputs
                    if impurity==[True]:
                        impurity="True"
                    elif impurity in [[False],[None]]:
                        impurity="False"
                    break

            # print(impurity,target)
            if target in impurity:
                impurity='ERROR_SAMEASTARGET'
        else:
            impurity='ERROR_PROCESSING'

        reactions.append({"target":target,"impurity_phase":impurity,"precursors":precs})
    return reactions
# list1 = '["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | ["Bi2(Mn,Fe)4O9 + δ", "(Mn,Fe)2O3"]","Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | ["Bi2(Mn,Fe)4O9 + δ", "(Mn,Fe)2O3"]"]'
# list1 = '["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False"]'
# list1 = '["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False","Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False"]'
# # list1 = '["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | [Bi2(Mn,Fe)4O9 + δ, (Mn,Fe)2O3]","Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False"]'
# list1 = '["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | ["Bi2(Mn,Fe)4O9 + δ", "(Mn,Fe)2O3"]","Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False"]'
# list1 = '["Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | ["BiMnFe2O6"]","Bi2O3 + Mn2O3 + Fe2O3 == BiMnFe2O6 | False"]'
# list1='["Ba + Sr + Co + Fe + Zr == Ba0.5Sr0.5(Co0.8Fe0.2)0.97Zr0.03O3−δ | [True]"]'
# list1='[]'

# parse_RxnImpoutput(list1)

# should get target elements using material parser for halluc_filter
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import json

dois_impurity, dois_impuritytrue, dois_impurityfalse = [], [], []  
def process_dat(dat):
    """Worker: classify and process a single dat."""
    local_counthere = 0
    newdat = dat.copy()
    error_parserxn = False

    if dat.get(f'gpt{GPTV}') is None:
        newdat['output'] = 'missing gpt output'
        return {"category": "error", "newdat": newdat, "rxns": []}

    try:
        if dat[f'gpt{GPTV}'] == '[]':
            newdat['output'] = 'blank output'
            return {"category": "blank", "newdat": newdat, "rxns": []}

        output = parse_RxnImpoutput(dat[f'gpt{GPTV}'])

        if isinstance(output, int):
            newdat['output'] = 'error output: ' + str(dat[f'gpt{GPTV}'])
            return {"category": "error", "newdat": newdat, "rxns": []}

        for rxn in output:
            if 'ERROR' in rxn['impurity_phase']:
                error_parserxn = True
        if error_parserxn:
            newdat['output'] = 'error output: ' + str(dat[f'gpt{GPTV}'])
            return {"category": "error_parserxn", "newdat": newdat, "rxns": []}

    except Exception:
        newdat['output'] = 'error processing output: ' + str(dat[f'gpt{GPTV}'])
        return {"category": "error", "newdat": newdat, "rxns": []}


    # hallucination filter
    if 'output' not in dat:#unmasked file
        rxns_inthisinput = []
        for rxn in output:
            elements = dat.get('target_elements', [])
            if 'target_elements' in dat:
                hallucresult = halluc_filter(dat['input'], rxn, elements=elements[:], mode='elements_target')
            else: #discard papers with erroneous target material detection
                hallucresult=True
                local_counthere += 1

            if not hallucresult:# append non hallucinated reactions
                rxns_inthisinput.append(rxn)

        if not rxns_inthisinput:  # all rxns for this DOI hallucinated, discard this DOI
            newdat['output'] = output
            newdat['error'] = 'halluc'
            return {"category": "halluc", "newdat": newdat, "rxns": []}
        
    else: # masked file. 'output' already has hallucination filtered output
        newdat['hallcinated']=dat['hallucinated']
        if dat['hallucinated']:
            rxns_inthisinput = []
            return {"category": "halluc", "newdat": newdat, "rxns": []}
        else:
            rxns_inthisinput = deepcopy(dat['output'][:])
    # keep filtered
    newdat['output'] = rxns_inthisinput

    # classify
    if any(isinstance(rxn['impurity_phase'], list) for rxn in rxns_inthisinput):
        return {"category": "impurityphase", "newdat": newdat, "rxns": rxns_inthisinput, "counthere": local_counthere}
    elif any(rxn['impurity_phase'] == 'True' for rxn in rxns_inthisinput):
        return {"category": "impurityTrue", "newdat": newdat, "rxns": rxns_inthisinput, "counthere": local_counthere}
    else:
        return {"category": "impurityFalse", "newdat": newdat, "rxns": rxns_inthisinput, "counthere": local_counthere}

with jsonlines.open(GPT4O_OUTPUTFILE, 'r') as f:
    newdats_orig = [dat for dat in f]

# --- main parallel execution ---
n_workers = max(1, cpu_count() // 2)

# counters
countblank = counterror = counterror_parserxn = counthalluc = countother = 0
rxns_impurity, rxns_impurityTrue, rxns_impurityFalse = [], [], []

with Pool(n_workers) as pool, \
     open(POSTPROCESSED_FILE, "w") as f_out, \
     (open(GPT4O_OUTPUTFILE_MASKED, "w") if flag_halluc_filter else nullcontext()) as f_out_masked:

    results_iter = pool.imap(process_dat, newdats_orig, chunksize=10)
    counthere = 0

    for res in tqdm(results_iter, total=len(newdats_orig)):
        cat, newdat, rxns = res["category"], res["newdat"], res["rxns"]

        if flag_halluc_filter:
            # mark hallucinated
            newdat['hallucinated'] = ('error' in newdat and newdat['error'] == 'halluc')
            for key in ['error','input', 'synthesis_pars']:# leave 'output' for use
                newdat.pop(key, None)

            f_out_masked.write(json.dumps(newdat) + "\n")

        counthere += res.get("counthere", 0)
        if cat == "blank":
            countblank += 1
        elif cat == "error":
            counterror += 1
        elif cat == "error_parserxn":
            counterror_parserxn += 1
        elif cat == "halluc":
            counthalluc += 1
        elif cat == "impurityphase":
            dois_impurity.append(1)
            # rxns_impurity.extend(rxns)
            f_out.write(json.dumps(newdat) + "\n")
        elif cat == "impurityTrue":
            dois_impuritytrue.append(1)
            # rxns_impurityTrue.extend(rxns)
            f_out.write(json.dumps(newdat) + "\n")
        elif cat == "impurityFalse":
            dois_impurityfalse.append(1)
            # rxns_impurityFalse.extend(rxns)
            f_out.write(json.dumps(newdat) + "\n")
        else:
            countother += 1

print("\nblank ", countblank,
      "\nerror ", counterror,
      "\nerrorparse ", counterror_parserxn,
      "\nhalluc ", counthalluc)
print("rest ", len(dois_impurity), len(dois_impuritytrue), len(dois_impurityfalse))

