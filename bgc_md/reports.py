# vim:set ff=unix expandtab ts=4 sw=4:
import numpy as np
import multiprocessing
import yaml
from pathlib import Path
import subprocess
from os.path import relpath, dirname
import os
import getopt, sys
from sympy import sympify, solve, Symbol, limit, oo, ceiling, simplify, Matrix
from sympy.core import Atom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import argparse
from bgc_md.DataFrame import DataFrame
from bgc_md.ReportInfraStructure import ReportElementList, Header, Math, Meta, Text, Citation, Table, TableRow, Newline, MatplotlibFigure
from bgc_md.Model import Model, check_parameter_set_complete
from bgc_md.ModelList import ModelList
#import bgc_md.bibtex as bibtex
import bgc_md.bibtexc as bibtexc
from bgc_md.helpers import py2tex_silent, key_from_dict_by_value
from bgc_md.plot_helpers import add_xhist_data_to_scatter
from bgc_md.gv import indexcolors, filled_markers
from CompartmentalSystems.bins.TsTpMassFieldsPerPoolPerTimeStep import TsTpMassFieldsPerPoolPerTimeStep
from CompartmentalSystems.bins.TimeStepIterator import TimeStepIterator

#import mpld3 # interesting functionality for interactive web figures

def generate_model_run_report(com=None):
    if com==None:
        com = parse_args()
    if com.t:
    # a target dir is given
        target_dir = com.t
        for yaml_file_name in com.f:
            print("Creating report from " + yaml_file_name + " to " + target_dir)
            create_single_report(yaml_file_name, target_dir)
        sys.exit(0)

    else:
        #print(com.f)
        #infer targetdirs from filenames
        for yaml_file_name in com.f:
            target_dir_path=Path(yaml_file_name).parent
            html_dir_path = target_dir_path.joinpath("html")
            create_single_report(yaml_file_name, html_dir_path.as_posix())
        sys.exit(0)

def defaults():
    this=Path(__file__).parents[0] #the package dir
    soilModelPath=this.joinpath("SoilModels")
    soilModelDir=soilModelPath.as_posix()
    vegModelPath=this.joinpath("VegetationModels") 
    vegModelDir=vegModelPath.as_posix()
    soilMsg='generating soil model website to '
    vegMsg='generating vegetation model website to '
    return {
         "dirs":{"veg":vegModelDir,"soil":soilModelDir}
        ,"msgs":{"veg":vegMsg,"soil":soilMsg}
        ,"paths":{"veg":vegModelPath,"soil":soilModelPath}
        }
def generate_model_run_reports(com):
    if com==None:
        com = parse_args()

    if com.v:
        print(defaults()['msgs']['veg'])
        generate_html_dir(defaults()['dirs']["veg"],com.t)
        sys.exit(0)

    if com.s: 
         print(defaults()['msgs']['soil'])
         generate_html_dir(defaults()['dirs']['soil'],com.t)
         sys.exit(0)
    
    if not(com.s or com.v): 
    # the default: if neither -v or -s is specified build the whole website
        print(defaults()['msgs']['veg'])
        generate_html_dir(defaults()['dirs']['veg'],com.t)
        print(defaults()['msgs']['soil'])
        generate_html_dir(defaults()['dirs']['soil'],com.t)
        sys.exit(0)

def generate_miniaml_model_reports(com):
   pass 
def generate_miniaml_model_report(com):
   pass 
    
def read_models_from_directory(input_dir):
    input_path = Path(input_dir)

    if not input_path.exists():
        raise(Exception("The input path " + input_path.as_posix() + " does not exist."))
    
    yaml_file_list = [f for f in input_path.iterdir() if f.suffix == ".yaml"]
    yaml_file_name_list = [str(f) for f in yaml_file_list]
    # fixme check if str(f) yields some os dependent path string representation
    # if so fix it 
    
    model_list = [Model.from_file(yaml_file_name)  for yaml_file_name in yaml_file_name_list]
    return(model_list)


def report_from_model(model):
    #rel = model.get_meta_data_report()
    rel = Meta(model.long_name, model.name, model.version)
    rel+= Header("General Overview", 1)

    reservoir_model = model.reservoir_model
    if reservoir_model:
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        rel += MatplotlibFigure(reservoir_model.figure(logo=True), "Logo", show_label=False, transparent=True)
        #logofig = reservoir_model.figure(logo=True)
        #logofig.savefig('ICBM_logo.svg', transparent=True)
        #plt.show(logofig)
        #print('Logo printed')

    rel+= Text(r"This report is the result of the use of the Python 3.4 package Sympy (for symbolic mathematics), as means to translate published models to a common language. It was created by $curator (Orcid ID: $Oid) on $entryDate, and was last modified on $modDate." + "\n",
            curator=model.entryAuthor,
            entryDate=model.entry_creation_date,
            modDate=model.last_modification_date,
            Oid=model.entryAuthor_orc_id,
             )

    if model.model_type == "vegetation_model": modType = "carbon allocation"
    if model.model_type == "soil_model": modType = "soil organic matter decomposition"

    if model.approach:
            article = "a"
            if model.approach[0] in "aeiou":
                article = "an"
            modApproach = " with " + article + " " + model.approach + " approach."
    else:
                modApproach = "."

    rel += Header("About the model", 2)
    rel += Text(r"The model depicted in this document considers $modType$modApproach It was originally described by ", 
                modType=modType, modApproach=modApproach)
    rel += Citation(model.bibtex_entry, parentheses=False) + Text(".  \n")

    # fixme: further references
    # include further references
    if model.further_references:
        rel += Header("Further references" , 3)
        for ref_dict in model.further_references:
            rel += Citation(ref_dict['bibtex_entry'], parentheses=False)
            if 'desc' in ref_dict.keys():
                rel += Text(": $desc", desc=ref_dict['desc'])
            rel += Text("\n")

    # include the abstract
    if model.abstract:
        rel += Header("Abstract", 3)
        rel += Text("$abstract", abstract=model.abstract+"\n")

    # include keywords
    if model.keywords:
        rel += Header("Keywords", 3)
        rel += Text("$k\n", k = (", ").join(model.keywords))

    # include principles
    if model.principles:
        rel += Header("Principles", 3)
        rel += Text("$k\n", k = (", ").join(model.principles))

    # include spaceScale:
    if model.spaceScale:
        rel += Header("Space Scale", 3)
    
        space_scale = model.spaceScale
        if type(space_scale) == type(""):
            space_scale = [space_scale]
        rel += Text("$k\n", k = (", ").join(space_scale))

    # include information on available parameter sets
    if model.parameter_sets:
        desc_exists = False
        colname_list = [Text("Abbreviation")]
        format_list = ["l"]
        for par_set in model.parameter_sets:
            sources_exist = False
            desc_exists = False
            if 'bibtex_entry' in par_set.keys() and par_set['bibtex_entry']: sources_exist = True
            if 'desc' in par_set.keys() and par_set['desc']: desc_exists = True

        if desc_exists:
            colname_list.append(Text("Description"))
            format_list.append("l")
        if sources_exist:
            colname_list.append(Text("Source"))
            format_list.append("l")
    
        # show this section only if additional information to the parameter sets is given
        if len(colname_list)>1:
            rel += Header("Available parameter values", 3)
            headers_row = TableRow(colname_list)
            T = Table(" Information on given parameter sets", headers_row, format_list)
            for par_set in model.parameter_sets:
                l = [Text(par_set['table_head'])]
                if desc_exists: 
                    if par_set['desc']:
                        l.append(Text(par_set['desc']))
                    else:
                        l.append(Text(" "))

                if sources_exist: 
                    if par_set['bibtex_entry']:
                        l.append(Citation(par_set['bibtex_entry'], parentheses=False))
                    else:
                        l.append(Text(" "))

                tr = TableRow(l)
                T.add_row(tr)    
            rel += T

    # include information on available initial values sets
    if model.initial_values:
        desc_exists = False
        colname_list = [Text("Abbreviation")]
        format_list = ["l"]
        for par_set in model.initial_values:
            if 'bibtex_entry' in par_set.keys() and par_set['bibtex_entry']: sources_exist = True
            if 'desc' in par_set.keys() and par_set['desc']: desc_exists = True

        if desc_exists:
            colname_list.append(Text("Description"))
            format_list.append("l")
        if sources_exist:
            colname_list.append(Text("Source"))
            format_list.append("l")
    
        # show this section only if additional information to the initial values sets is given
        if len(colname_list)>1:
            rel += Header("Available initial values", 3)
            headers_row = TableRow(colname_list)
            T = Table(" Information on given sets of initial values", headers_row, format_list)
            for par_set in model.initial_values:
                l = [Text(par_set['table_head'])]
                if desc_exists: 
                    if par_set['desc']:
                        l.append(Text(par_set['desc']))
                    else:
                        l.append(Text(" "))

                if sources_exist: 
                    if par_set['bibtex_entry']:
                        l.append(Citation(par_set['bibtex_entry'], parentheses=False))
                    else:
                        l.append(Text(" "))

                tr = TableRow(l)
                T.add_row(tr)    
            rel += T

    # show the secions of the model data
    for section_name in model.sections:
        if section_name == 'state_variables':
            rel += Header(model.section_titles[section_name], 1)
            rel += Text("The following table contains the available information regarding this section:")
            rel += model.state_variables_Table()
        elif section_name == 'additional_variables':
            rel += Header(model.section_titles[section_name], 1)
            rel += Text("The following table contains the available information regarding this section:")
            rel += model.additional_variables_Table()
        elif section_name == 'allocation_coefficients':
            rel += Header(model.section_titles[section_name], 1)
            rel += Text("The following table contains the available information regarding this section:")
            rel += model.allocation_coefficients_Table()
        elif section_name == 'components':
            rel += Header(model.section_titles[section_name], 1)
            rel += Text("The following table contains the available information regarding this section:")
            rel += model.components_Table()
        elif section_name == 'parameter_sets':
            # parameter_sets are treated completely differently
            pass
        else:
            # custom section to be included in the report
            rel += Header(model.section_titles[section_name], 1)
            rel += Text("The following table contains the available information regarding this section:")
            rel += model.variables_Table_from_section(section_name, parameter_values = True)

    # include pool model plot
    if reservoir_model:
        inputs = reservoir_model.input_fluxes
        outputs = reservoir_model.output_fluxes
        internal_fluxes = reservoir_model.internal_fluxes
#        inputs, outputs, internal_fluxes = model.fluxes

        rel += Text("\n")
        rel += Header("Pool model representation", 2)

        header = [Text("Pool model"), Text("Fluxes")]
        header_row = TableRow(header)
        T = Text("<table>")
        T += Text("<thead>")
        T += Text("<tr><th></th><th>Flux description</th></tr>")
        T += Text("</thead><tbody>")
        T += Text("<tr>")
        T += Text("<td align=center, style='vertical-align: middle'>")  
        fig = reservoir_model.figure(figure_size=(7,7))
        fig_rel = MatplotlibFigure(fig, "Figure 1", "Pool model representation")
        #T += fig_rel.pandoc_markdown()
        T += fig_rel
        T += Text("</td><td align=left style='vertical-align: middle'>")
        
        # write the fluxes to the table
        legend = ReportElementList([])

        # input fluxes
        if len(inputs) > 0:
            legend += Header("Input fluxes", 4)
            for pool, flux in inputs.items():
                legend += Math("$v: $f", v=py2tex_silent(model.state_variables[pool]), f=flux)
                legend += Newline()
        
        # output fluxes
        if len(outputs) > 0:
            legend += Text("\n")
            legend += Header("Output fluxes", 4)
            for pool, flux in outputs.items():
                legend += Math("$v: $f", v=py2tex_silent(model.state_variables[pool]), f=flux)
                legend += Newline()
        
        # internal fluxes
        if len(internal_fluxes) > 0:
            legend += Text("\n")
            legend += Header("Internal fluxes", 4)
            if_sorted = [((i,j), f) for (i,j), f in internal_fluxes.items()]
            if_sorted = sorted(if_sorted, key=lambda el: (el[0][0],el[0][1]))
            for (pfrom, pto), flux in if_sorted:
                legend += Math("$pf \\rightarrow $pt: $f", pf=py2tex_silent(model.state_variables[pfrom]), pt=py2tex_silent(model.state_variables[pto]), f=flux)
                legend += Newline()
        
        T += legend
        T += Text("</td></tr>")
        T += Text("</tbody></table>")


        rel += T


    # include RHS and jacobian
    rel += Header("The right hand side of the ODE", 2)
    rel += Math("$eq", eq=model.rhs)
    rel += Text("\n")
    rel += Header("The Jacobian (derivative of the ODE w.r.t. state variables)", 2)
    rel += Math("$J", J=model.jacobian())

    rel += Text("\n")
 
    #fixme: suggested steady states  
    # check suggested steady states

#    rhs = model.rhs
#    sug_ss = model.complete_dict['suggested_steady_states']
#    sug_ss = {key: sympify(val, locals=model.symbols_by_type) for key, val in sug_ss[0].items()}
#    sug_ss.update({'alpha': 1, 'beta': 0.5, 'Phi_i': 0, 'Phi_o': 0, 'Phi_up': 0, 'Phi_l': 0, 'A': 5.2, 'r': 2, 's': 1, 'i':1})
#    ss = rhs.subs(sug_ss)
#    for i in range(len(ss)):
#        ss[i] = simplify(ss[i])
#        print(ss[i])

    # try to calculate the steady states for ten seconds
    # after ten seconds stop it
    q = multiprocessing.Queue()
    def calc_steady_states(q):
#        rhs = Matrix(list(model.rhs)[1:])
#        sv = Matrix(list(model.state_vector['expr'])[1:])

        ss = solve(model.rhs, model.state_vector['expr'], dict=True)

#        ss = solve(rhs, sv, dict=True)
#        srhs = rhs.subs(ss[0])
#        for i in range(len(srhs)):
#            print(simplify(srhs[i]))
        q.put(ss)

    p = multiprocessing.Process(target=calc_steady_states, args=(q,))
    p.start()
    p.join(10)
    if p.is_alive():
        p.terminate()
        p.join()
        steady_states = []
    else:
        steady_states = q.get()

#    rhs = model.rhs
#    srhs = rhs.subs(steady_states[0])
#    for i in range(len(srhs)):
#        print(simplify(srhs[i]))
    

    # check if steady states have all state variables
#    formal_steady_states = []
#    for ss in steady_states:
#        if len(ss) == len(model.state_vector['expr']):
#            formal_steady_states.append(simplify(ss))

    formal_steady_states = steady_states
    if formal_steady_states:
        rel += Header("Steady state formulas", 2)
        for ss in formal_steady_states:
            for sv_symbol in model.state_vector['expr']:
                if sv_symbol in ss.keys():
                    ss[sv_symbol] = simplify(ss[sv_symbol])
                else:
                    ss[sv_symbol] = sv_symbol

                rel += Math("$name = $value", name=sv_symbol, value=ss[sv_symbol]) + Newline()
            rel += Newline()

    # include parameter set information: steady states, eigenvalues, damping ratios
#    complete_parameter_sets = [par_set for par_set in model.parameter_sets if check_parameter_set_complete(par_set, model.state_vector, model.time_symbol, model.state_vector_derivative)]
    
    if model.time_symbol:
        time_symbol = model.time_symbol['symbol']
    else:
        time_symbol = None

    complete_parameter_sets = model.parameter_sets
    if formal_steady_states and complete_parameter_sets:
        rel += Text("\n")
        rel += Header("Steady states (potentially incomplete), according jacobian eigenvalues, damping ratio", 2)
        for par_set in complete_parameter_sets:
            header_str = "Parameter set: " + par_set['table_head']
            rel += Header(header_str, 3)

            rhs = model.rhs
            steady_states = solve(rhs.subs(par_set['values']), model.state_vector['expr'], dict=True)
            #steady_states = solve(rhs, model.state_vector['expr'], dict=True)
            for ss in steady_states:
                # check if steady state calculation could solve for all state variables
#                if len(ss) == len(model.state_vector['expr']):
                    ss_list = []
                    for sv_symbol in model.state_vector['expr']:
                        if sv_symbol in ss.keys():
                            ss_expr = ss[sv_symbol]
                        else:
                            ss_expr = sv_symbol

                        if time_symbol in ss_expr.free_symbols:
                            # take limit of time to infinity if steady state still depends on time
                            ss_expr = limit(ss_expr, time_symbol, oo)
                            rel += Text("\nTaken limit ") + Math("$sv($t)", sv=sv_symbol, t=time_symbol)
                            rel += Text(" for ") + Math("$t", t=time_symbol)
                            rel += Text(" to infinity.\n\n")
    
                        sv_name = key_from_dict_by_value(model.symbols_by_type, sv_symbol)
    
                        ss_list.append({'name': sv_name, 'symbol': sv_symbol, 'value': ss_expr})
                        
                    for i in range(len(ss_list)):
                        if ss_list[i]['value'].free_symbols == set():
                            if ss_list[i]['value'] < 0:
                                rel += Text('<font color="FF0000">')
                                rel += Math(ss_list[i]['name'] + ": $v", v = round(ss_list[i]['value'], 3))
                                rel += Text('</font>')
                            else:
                                rel += Math(ss_list[i]['name'] + ": $v", v = round(ss_list[i]['value'], 3))
                        else:
                                rel += Math(ss_list[i]['name'] + ": $v", v = ss_list[i]['value'])
    
                        if i< len(ss_list)-1:
                            rel += Text(", ")
    
                    rel += Newline()*2
    
                    dic = par_set['values']
                    for i in range(len(ss_list)):
                        dic[ss_list[i]['name']] = ss_list[i]['value']
    
                    jacobian = model.jacobian().subs(dic)
                    if jacobian.free_symbols == set():
                        evs = [complex(v) for v in jacobian.eigenvals().keys()]
                    else:
                        evs = [v for v in jacobian.eigenvals().keys()]

                    for i in range(len(evs)):
                        ev = evs[i]
                        
                        if jacobian.free_symbols == set():
                            if ev.imag == 0:
                                ev = ev.real
    
                            lamda_i = Symbol('lamda_'+ str(i+1))
                            rel += Math("$s: $v", s = lamda_i, v = "{:.3f}".format(ev)) + Newline()
        
                            if ev.imag != 0:                        
                                rho = -ev.real/np.sqrt(ev.real**2+ev.imag**2)
                                rel += Math("$s: $v", s = Symbol("rho_"+ str(i+1)), v = "{:-3f}".format(rho)) + Newline()
                        else:
                            lamda_i = Symbol('lamda_'+ str(i+1))
                            rel += Math("$s: $v", s = lamda_i, v = ev.evalf(4)) + Newline()
        
                            #if ev.imag != 0:                        
                            #    rho = -ev.real/np.sqrt(ev.real**2+ev.imag**2)
                            #    rel += Math("$s: $v", s = Symbol("rho_"+ str(i+1)), v = "{:-3f}".format(rho)) + Newline()
    
        
                    rel += Text("\n")*2
                        

    #fixme
#    steady_states=solve(model.rhs, model.state_vector['expr'], dict=True)

    # include model simulations
    if reservoir_model and model.model_runs:
        rel += Header("Model simulations", 2)


        model_runs = model.model_runs
        for i, mr in enumerate(model_runs):
            comb = model.model_run_combinations[i]
            par_set = comb['par_set']['values']

            run_data_str_basis = "Initial values: " + comb['IV']['table_head']
            run_data_str_basis += ", Parameter set: " + comb['par_set']['table_head']

            # plot solutions
            fig = plt.figure(figsize=(7,3*len(model.state_vector["expr"])), tight_layout=True)          
#            time_unit = model.df.get_by_cond('unit', 'name', model.time_symbol['name'])
#            units = [model.df.get_by_cond('unit', 'name', sv.name) for sv in model.state_vector['expr']]
#            mr.plot_sols(fig, time_unit, units)
# fixme:mm-30.01.2018            mr.plot_sols(fig)

            label = "Model run " + str(i+1) + " - solutions"
            run_data_str = run_data_str_basis + ", Time step: " + str(comb['run_time']['step_size'])
            rel += MatplotlibFigure(fig, label, run_data_str)
            
            # plot phase planes
            fig = plt.figure(figsize=(3*len(model.state_vector["expr"]),7), tight_layout=True)
#            mr.plot_phase_planes(fig, units)
            mr.plot_phase_planes(fig)

            label = "Model run " + str(i+1) + " - phase planes"
            run_data_str = run_data_str_basis + ", Start: " + str(comb['run_time']['start'])
            run_data_str += ", End: " + str(comb['run_time']['end'])
            run_data_str += ", Time step: " + str(comb['run_time']['step_size'])
            rel += MatplotlibFigure(fig, label, run_data_str)

            # plot external input 
#            fig = plt.figure(figsize=(7,3), tight_layout=True)
#            label = "Model run " + str(i+1) + " - external input"
#            mr.plot_external_input_fluxes(fig)
#            rel += MatplotlibFigure(fig, label, run_data_str)

            # plot system-age distributions
            fig = plt.figure(figsize=(10,15), tight_layout=True)
#            fig = plt.figure(figsize=(6,6), tight_layout=True)
            tsi=TimeStepIterator.from_ode_reservoir_model_run(mr)
            
            age_dist_hist=TsTpMassFieldsPerPoolPerTimeStep.from_time_step_iterator(tsi)
            print("Calculation done, creating plot.")
            age_dist_hist.matrix_plot3d("plot_system_age_distributions_with_bins", fig, title="System age distribution", mr=mr)
            print("Plot created.")
            
            label = "Model run " + str(i+1) + " - system-age-distributions"
            
            rel += MatplotlibFigure(fig, label, run_data_str_basis)
            #fig.show()
            #input()

    # include references
    rel += Text("\n")
    rel += Header("References", 1)
    return(rel)
    
######################################################################

def input_output_path(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        raise(Exception("The input path " + input_path + " does not exist."))

    if not output_path.exists():
        output_path.mkdir()

    return input_path, output_path


def produce_model_report_markdown(yaml_file_name_list, md_file_name_list):
    if type(yaml_file_name_list) == type(""):
        yaml_file_name_list = [yaml_file_name_list]
    if type(md_file_name_list) == type(""):
        md_file_name_list = [md_file_name_list]

    if len(yaml_file_name_list) != len(md_file_name_list):
        raise(Exception("Length if input file list does not equal length of output file list."))

    for index, yaml_file_name in enumerate(yaml_file_name_list):
        md_file_name = md_file_name_list[index]
        with open(yaml_file_name) as f:
            yaml_str = f.read()

        rel, references = report_from_yaml_str(yaml_str)

        trunk = Path(md_file_name).stem
        bibtex_file_name = os.path.join(dirname(md_file_name), trunk + ".bibtex")
        bibtexc.entry_list_to_file(bibtex_file_name, references, format_str="BibTeX")
        rel.write_pandoc_markdown(md_file_name)   
 

def report_from_yaml_str(yaml_str):
    complete_dict = yaml.load(yaml_str)
    model = Model(complete_dict)
    return report_from_model(model)
    
 
def produce_model_report_markdown_directory(input_dir, output_dir):
    input_path, output_path = input_output_path(input_dir, output_dir)

    yaml_file_list = [f for f in input_path.iterdir() if f.suffix == ".yaml"]
    md_file_list = [output_path / (f.stem + ".md") for f in yaml_file_list]

    yaml_file_name_list = [str(f) for f in yaml_file_list]
    md_file_name_list = [str(f) for f in md_file_list]
    produce_model_report_markdown(yaml_file_name_list, md_file_name_list)


def create_html_from_pandoc_md(md_file_name_list, html_file_name_list, csl_file_name = "", css_file_name = "", slide_show = False):
    if type(md_file_name_list) == type(""):
        md_file_name_list = [md_file_name_list]
    if type(html_file_name_list) == type(""):
        html_file_name_list = [html_file_name_list]

    if len(md_file_name_list) != len(html_file_name_list):
        raise(Exception("Length if input file list does not equal length of output file list."))

    for index, md_file_name in enumerate(md_file_name_list):
        html_file_name = html_file_name_list[index]
        trunk = Path(md_file_name).stem
        bibtex_file_name = os.path.join(dirname(md_file_name), trunk + ".bibtex")

        cmd = ["pandoc"]
        cmd += [md_file_name,"-s","--mathjax", "-o", html_file_name]        
        cmd += ["--filter=pandoc-citeproc", "--bibliography="+bibtex_file_name]
        if css_file_name: 
            rel_css_folder = relpath(dirname(css_file_name), dirname(html_file_name))
            rel_css_file_name = os.path.join(rel_css_folder, os.path.split(css_file_name)[1])
            cmd += ["-c", rel_css_file_name]

        if csl_file_name: cmd += ["--csl", csl_file_name]
        if slide_show: cmd += ["-t", "slidy"]
            # "slidy" can be changed to: "s5", "slideous", "dzslides", or "revealjs". 
            # For generating a beamer, we'll need: (["pandoc","-t","beamer","--mathjax",md_file,"-o","pdf"]), 
            # where md_file should have TeX math embedded.

        try:
            subprocess.check_call(["rm","-rf", html_file_name])
            subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            out=e.output
            print(out)


def create_html_from_pandoc_md_directory(input_dir, output_dir, csl_file_name = "", css_file_name = "", slide_show = False):
    input_path, output_path = input_output_path(input_dir, output_dir)

    md_file_list = [f for f in input_path.iterdir() if f.suffix == ".md"]
    html_file_list = [output_path / (f.stem + ".html") for f in md_file_list]

    md_file_name_list = [str(f) for f in md_file_list]
    html_file_name_list = [str(f) for f in html_file_list]
    create_html_from_pandoc_md(md_file_name_list, html_file_name_list, csl_file_name=csl_file_name, css_file_name=css_file_name, slide_show=slide_show)


#fixme: probably working through side effects
def nice_hist(ax, data):
    bins = [i for i in range(min(data),max(data)+2,1)]
    his = np.histogram(data,bins=bins)
    ax.bar(his[1][:-1],his[0], width=1.0, align='center', color='g', alpha=0.75)
    ax.set_xticks(bins[:-1])
#    plt.xticks(bins[:-1], bins[:-1])
    ax.set_yticks(range(max(his[0])+1))
#    ax.hist(data, number_of_bins, normed=0, histtype='bar', facecolor='g', alpha=0.75)
    ax.set_xlim([bins[0]-0.5, bins[-1]-0.5])
    locator = MaxNLocator(nbins=10, integer=True)
    ax.xaxis.set_major_locator(locator)


def add_yhist_data_to_scatter(plot_ax, data, label, fontsize, show_grid = True):
    # add right y-axis with histogram data

    # add second y-axis at the right
    ax = plot_ax.twinx()
    ax.set_position(plot_ax.get_position())
    ax.set_ylim(plot_ax.get_ylim())

    # prepare data
    bins = [i for i in range(min(data),max(data)+2,1)]
    hisy = np.histogram(data,bins=bins)

    y2_ticks = [hisy[1][i] for i in range(len(hisy[0])) if hisy[0][i] != 0]
    y2_ticklabels = [hisy[0][i] for i in range (len(hisy[0])) if hisy[0][i] !=0]
    ax.set_yticks(y2_ticks)
    ax.set_yticklabels(y2_ticklabels, fontsize=fontsize)
    ax.set_ylabel(label, fontsize=fontsize)
    ax.grid(show_grid)


# fixme: what does this function really count?
def depth(expr):
    expr = sympify(expr)

    if isinstance(expr, Atom):
        return 1
    else:
        if len(expr.args) == 0:
            return 0
        return 1 + max([depth(arg) for arg in expr.args])


def create_model_list_report_html(model_list, output_file_name, html_dir_path):
    # vegetation or soil models?
    model_type = model_list[0].model_type

    output_path = Path(dirname(output_file_name))
    if not output_path.exists():
        output_path.mkdir()

    rel = Header('Overview of the models', 1)

    header = [Text(""), Text("Model"), Text("# Variables"), Text("# Parameters"), Text("# Constants"), Text("Component"), Text("Description"), Text("Expressions"), Text("fv/fs"), Text("Right hand side of ODE"), Text("Source")]
    table_format = list("lcccclcccl")

    rel2 = Text('''<script language="javascript">
    function ausklappen(id)
    {
        if (document.getElementById(id).style.display=="none")
        {
            document.getElementById(id).style.display="block";
        }
        else
        {
            document.getElementById(id).style.display="none";
        }
    }\n</script>\n''')

    rel2 += Text('<table>\n<thead><tr class="header">\n<th></th><th align="left">Model</th>\n<th align="center"># Variables</th>\n<th align="center"># Parameters</th>\n<th align="center"># Constants</th>\n<th align="center">Structure</th>\n<th align="center">Right hand side of ODE</th>\n<th align="left">Source</th>\n</tr>\n</thead>\n')
       
    header_row = TableRow(header)
    T = Table("Summary of the models in the database of Carbon Allocation in Vegetation models", header_row, table_format)

    compar_keys=["state_vector_derivative"]
    plot_data = DataFrame([['name', 'nr_sv', 'nr_sym', 'nr_exprs', 'nr_ops', 'depth','nr_vars','nr_parms','part_scheme','s_scale','t_resol']+compar_keys])
    for index, model in enumerate(model_list):
        print(model.name)
        # collect data for plots
        data_list = [model.name]

        nr_state_v = 0
        for sec in model.sections:
            if sec == "state_variables":
                nr_state_v = model.section_vars('state_variables').nrow
        
        ops = 0
        d = 0
        for i in range(model.rhs.rows):
            for j in range(model.rhs.cols):
                ops += model.rhs[i,j].count_ops()
                d = max([d, depth(model.rhs[i,j])])

        
        if model.partitioning_scheme == "fixed": 
            boolean_part_scheme = 0
        else:
            boolean_part_scheme = 1
        state_vector_derivative_dep_set={"faked_key","another_faked_key"}

        data_list += [nr_state_v, len(model.syms_dict), len(model.exprs_dict), ops, d,len(model.variables),len(model.parameters),boolean_part_scheme,model.space_scale,model.time_resolution,state_vector_derivative_dep_set]
        plot_data.append_row(data_list)
        
        # create table
        dir_name = model.bibtex_entry.key
        if model.modelID: dir_name += "-" + model.modelID
        report_link = Path(dir_name).joinpath("Report.html").as_posix()

        l = [Text(model.name)]         
        rel2 += Text('<tbody>\n')
        parity = ['odd','even'][(index+1) % 2]
        rel2 += Text('<tr class="$p">\n', p=parity, i=index)

        image_string = ""
        reservoir_model = model.reservoir_model
        if reservoir_model:
            image_file_path = Path(dir_name).joinpath("Thumbnail.svg")
            fig = reservoir_model.figure(thumbnail=True)
            fig.savefig(html_dir_path.joinpath(image_file_path).as_posix(), transparent=True)
            plt.close(fig)
            image_string = '<img src="' + image_file_path.as_posix() + '"> '

        rel2 += Text('<td align="left">$image_string</td>', image_string=image_string)
        rel2 += Text('<td align="left"><a href="$rl" target="_blank">$mn</a></td>\n', rl=report_link, mn=model.name)

        l.append(Text(str(len(model.variables))))
        rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">$n</td>\n', i=index, n=str(len(model.variables)))

        l += [Text(" ")]*5
        rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">$n</td>\n', i=index, n=str(len(model.parameters)))
        rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')"></td>\n', i=index)

        fv_fs_entry = Text(" ")
        for row_dic in model.df.rows_as_dictionary:
            if row_dic['name'] in ('f_v', 'f_s'):
                if 'exprs' in row_dic.keys() and row_dic['exprs']:
                    fv_fs_entry = exprs_to_element(row_dic['exprs'], model.symbols_by_type)
        l.append(fv_fs_entry)

        l.append(Math("$eq", eq=model.rhs))
        rest = Text('<td align="center" style="vertical-align:middle" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')"><div id="rhs_$i" style="display:none">', i=index) + Math("$eq", eq=model.rhs) + Text("</div></td>\n")
        l.append(Citation(model.bibtex_entry, parentheses=False))
        rest += Text('<td align="left" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">', i=index) + Citation(model.bibtex_entry, parentheses=False) + Text("</td>\n</tr>\n")
        row = TableRow(l)
        T.add_row(row)

        rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">', i=index) + fv_fs_entry
        rel2 += Text('\n<div id="comp_table_$i" style="display:none">\n',i=index)
        comp_t = Text('<table>\n<tr class="header">\n<th align="center">Component</th>\n<th align="left">Description</th>\n<th align="center">Expressions</th>\n</tr>\n</thead>\n')
        comp_t += Text("<tbody>\n")
        is_comp = False
        for row_dic in model.df.rows_as_dictionary:
            if row_dic['category'] in ('components') and row_dic['name'] not in ('fv', 'fs'):
                is_comp = True
                l = [Newline()]*4

                l.append(Math("$sv", sv=sympify(row_dic['name'], locals=model.symbols_by_type)))
                comp_t += Text('<tr>\n<td align="center">') +Math("$sv", sv=sympify(row_dic['name'], locals=model.symbols_by_type)) + Text("</td>\n")

                if row_dic['desc']:
                    l.append(Text("$d" , d=row_dic['desc']))
                    comp_t += Text('<td align="left">$d</td>\n',d=row_dic['desc'])
                else:
                    l.append(Text("-"))
                    comp_t += Text('<td align="left">-</td>\n')

                if row_dic['exprs']:
                    l.append(exprs_to_element(row_dic['exprs'], model.symbols_by_type))
                    comp_t += Text('<td align="center">') + exprs_to_element(row_dic['exprs'], model.symbols_by_type) + Text("</td>\n")
                else:
                    l.append(Text("-"))
                    comp_t += Text('<td align="center">-</td>\n')

                l += [Newline()]*3

                row = TableRow(l)
                T.add_row(row)                    
                comp_t += Text("</tr>\n")

        comp_t += Text("</tbody>\n</table>\n</td>\n")
        if is_comp:
            rel2 += comp_t
        rel2 += Text("</div>\n")
        rel2 += rest

    #rel += T
    rel2 += Text("</tbody>\n</table>\n")
    rel += rel2

    # create the plots

    rel += Header("Figures", 1)

    # first line of histograms
    nr_hist = 3
    fig1 = plt.figure(figsize=(15,5), tight_layout=True)

    # state variables and models
    ax = fig1.add_subplot(1, nr_hist, 1)
    data = np.array(plot_data[:,'nr_sv'])
    nice_hist(ax, data)
    ax.set_xlabel("# state variables", fontsize = "22",  labelpad=20)
    ax.set_ylabel("# models", fontsize = "22",  labelpad=20)
    # change font size for the tick labels
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(20) 
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(20) 

    # parameters and models
    ax = fig1.add_subplot(1, nr_hist, 2)
    data = np.array(plot_data[:,'nr_parms'])
    nice_hist(ax, data)
    ax.set_xlabel("# parameters", fontsize = "22",  labelpad=20)
    ax.set_ylabel("# models", fontsize = "22",  labelpad=20)
     
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(20) 
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(20) 

    # variables and models
    ax = fig1.add_subplot(1, nr_hist, 3)
    data = np.array(plot_data[:,'nr_vars'])
    nice_hist(ax, data)
    ax.set_xlabel("# variables", fontsize = "22",  labelpad=20)
    ax.set_ylabel("# models", fontsize = "22",  labelpad=20)

    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(20) 
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(20) 

    # variables and models
    #rel += Text(mpld3.fig_to_html(fig1))
    rel += MatplotlibFigure(fig1,"Figure 1","Histograms, # variables") 

#    # second line 
#    target_key="state_vector_derivative"
#    sublist=ModelList([m for m in model_list if m.has_key(target_key)])
#    nr_hist = 2
#    fig1 = plt.figure(figsize=(30,15), tight_layout=True)
#    ax = fig1.add_subplot(nr_hist,1,1)
#    # first check wich models actually provide the target_key we are looking for
#    sublist.plot_dependencies(target_key,ax)
#    ax = fig1.add_subplot(nr_hist,1,2)
#    sublist.plot_model_key_dependencies_scatter_plot(target_key,ax)
#
#    rel += MatplotlibFigure(fig1,"Figure 2","Dependencies of the right hand side of the ODEs") 
#
#    fig1 = plt.figure(figsize=(30,1), tight_layout=True) 
#    plt.rcdefaults()
#    # note that the second argument 1 in figsize is required by matplotlib 
#    # but ignored by the following method because the 
#    # height will be adapted inside the method
#
#    ModelList(model_list).denpendency_plots_from_keys_in_compartments(fig1)
#    rel += MatplotlibFigure(fig1,"Figure 3","dependency plots of compartment variables") 
#

    # scatter plots
    xhist_fs = 16
    yhist_fs = 16

    # variables vs. parameters
    fig = plt.figure(figsize=(10,10))

    ax = fig.add_subplot(1,1,1)
    xdata = np.array(plot_data[:,'nr_vars'])
    ydata = np.array(plot_data[:,'nr_parms'])

    for i in range(plot_data.nrow):
        #ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], c=indexcolors[i+20])
        ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])

    box = ax.get_position()
    ax.set_position([box.x0, box.y0+box.height*0.4, box.width, box.height*0.6])
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -box.height*0.8), scatterpoints=1, frameon = False, ncol = 2)
    ax.set_xlabel("# variables", fontsize = "22",  labelpad=20)
    ax.set_ylabel("# parameters", fontsize = "22",  labelpad=20)
    ax.set_ylim((0,max(ydata)+1))

    # change font size for the tick labels
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(20) 
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(20) 

    add_xhist_data_to_scatter(ax, xdata, ' models', fontsize=xhist_fs)
    add_yhist_data_to_scatter(ax, ydata, ' models', fontsize=yhist_fs)

    rel += MatplotlibFigure(fig,"Figure 4", "# variables & parameters")

    # symbols and operations
    fig = plt.figure(figsize=(15,10))

    ax = fig.add_subplot(1,1,1)
    ModelList(model_list).scatter_plus_hist_nr_vars_vs_nr_ops(ax)
    if model_type == 'soil_model':
        ax.set_ylabel(' operations to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = 22)
    rel += MatplotlibFigure(fig,"Figure 4b", "# variables & # operations")

    # symbols and depth of operations
    fig = plt.figure(figsize=(10,10)) # figure size including legend

    ax = fig.add_subplot(1,1,1)
    xdata = np.array(plot_data[:,'nr_vars'])
    ydata = np.array(plot_data[:,'depth'])

    for i in range(plot_data.nrow):
        ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])

    box = ax.get_position()
    ax.set_position([box.x0, box.y0+box.height*0.4, box.width, box.height*0.6])
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -box.height*0.8), scatterpoints=1, frameon = False, ncol = 2)
#    ax.legend(loc='lower center', scatterpoints=1, frameon = False, ncol = 2)
    ax.set_xlabel("# variables", fontsize = "22",  labelpad=20)
    if model_type == 'vegetation_model':
        ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = 22)
    if model_type == 'soil_model':
        ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = 22)

    ax.set_ylim((0,max(ydata)+1))

    # change font size for the tick labels
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(20) 
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(20) 

    add_xhist_data_to_scatter(ax, xdata, ' models', fontsize=xhist_fs)
    add_yhist_data_to_scatter(ax, ydata, ' models', fontsize=yhist_fs)
    plt.rcdefaults()
    rel += MatplotlibFigure(fig,"Figure 5", "# variables & cascading depth of operations")

   
    # number of operations and depth of operations
    fig = plt.figure(figsize=(10,10))

    ax = fig.add_subplot(1,1,1)
    xdata = np.array(plot_data[:,'nr_ops'])
    ydata = np.array(plot_data[:,'depth'])


    for i in range(plot_data.nrow):
        #ax.scatter(xdata[i]+(0.5-np.random.rand(1))*0.75,ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], c=indexcolors[i+20])
        ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])

    box = ax.get_position()
    ax.set_position([box.x0, box.y0+box.height*0.4, box.width, box.height*0.6])
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -box.height*0.8), scatterpoints=1, frameon = False, ncol = 2)
    if model_type == 'vegetation_model':
        ax.set_xlabel(r' operations to calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = "22",  labelpad=20)
        ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = "22",  labelpad=20)
    if model_type == 'soil_model':
        ax.set_xlabel(r' operations to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = "22",  labelpad=20)
        ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = "22",  labelpad=20)
    ax.yaxis.labelpad = 0

    # change font size for the tick labels
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(20) 
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(20) 
    ax.set_ylim((0,max(ydata)+1))
    ax.set_xlim((0,max(xdata)+50))

#    add_xhist_data_to_scatter(ax, xdata, ' models')
    add_yhist_data_to_scatter(ax, ydata, ' models', fontsize=yhist_fs)
    rel += MatplotlibFigure(fig,"Figure 6", "cascading depth and # operations")

    # partitioning scheme and number of operations
    if model_type == 'vegetation_model':
        fig = plt.figure(figsize=(8,5))
        fig.subplots_adjust(bottom=0.2, top=0.8, left=0.2)
    
        ax = fig.add_subplot(1,1,1)
        xdata = np.array(plot_data[:,'part_scheme'])
        ydata = np.array(plot_data[:,'nr_ops'])
    
        for i in range(plot_data.nrow):
            #ax.scatter(xdata[i]+(0.5-np.random.rand(1))*0.1,ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], c=indexcolors[i+20])
            ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])
    
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.4, box.height])
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), scatterpoints=1, frameon=False)
        ax.set_xlabel("partitioning scheme", fontsize = "22", labelpad=25)
        ax.set_ylabel(' operations to\n' + r'calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = "22", labelpad=25)
    #    ax.yaxis.label.set_position([-0.2,0])
        ax.set_ylim((0,max(ydata)+10))
        ax.set_xlim((-0.2,max(xdata)+0.2))
        ax.set_xticks([0,1])
        ax.set_xticklabels(['fixed','dynamic'])
    
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(16) 
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(16) 
    
        add_xhist_data_to_scatter(ax, xdata, ' models', fontsize=16)
    
        rel += MatplotlibFigure(fig,"Figure 7", "Type of carbon partitioning scheme among pools and # operations")

    rel += Header("Bibliography", 1)
    rel.write_pandoc_html(output_file_name)


# needs a test
def exprs_to_element(exprs, symbols_by_type):
    if not exprs:
        return Text("-")

    # two possibilities in yaml file:
    # 1)    exprs: "C = ..."
    # 2)    exprs:
    #           - "C = ..."
    #           - "C = ..."
    # so this table entry will be treated as a list of expressions
    subl = ReportElementList([])
    if type(exprs) == type(""):
        expr_list = [exprs]
    elif type(exprs) == type([]):
        expr_list = exprs
    else:
        raise(Exception(str(exprs) + " is no valid list of expressions."))

    for index2, expr_string in enumerate(expr_list):
        if expr_string:
            # new line if not first entry
            if index2 > 0:
                subl.append(Newline()) 
            parts = expr_string.split("=",1)
            parts[0] = parts[0].strip()
            parts[1] = parts[1].strip()
            p1 = sympify(parts[0], locals=symbols_by_type)
            p2 = sympify(parts[1], locals=symbols_by_type)
            
            # this is a hybrid version that keeps 'f_s = I + A*C' in shape, but if 'Matrix(...)' comes into play, rearranging by sympify within the matrix cannot be prevented
            # comment it out for a a clean version regarding use of ReportElementList, but with showing 
            # 'f_s = A * C + I' instead
            try:
                p2 = py2tex_silent(parts[1])
            except TypeError:
               pass
            
            subl.append(Math("$p1=$p2", p1=p1,p2=p2))
    return subl


def generate_html_dir(source_dir, target_dir = None):
    if not target_dir:
        target_dir_path = Path(source_dir)
    else:
        target_dir_path = Path(target_dir)
    print("Targetdirectory: "+target_dir_path.as_posix())
    
    html_dir_path = target_dir_path.joinpath("html")
    html_dir = html_dir_path.as_posix()
    
    models = read_models_from_directory(source_dir)
    models.sort(key=lambda m: m.bibtex_entry.entry['year'])
    for model in models:
        print(model.name)
        dir_name = model.bibtex_entry.key
        if model.modelID: dir_name += "-" + model.modelID

        sub_dir = html_dir_path.joinpath(dir_name).as_posix()
        rel = report_from_model(model) 
        rel.create_pandoc_dir(sub_dir)

    if models[0].model_type == 'vegetation_model':
        list_file = html_dir_path.joinpath('list_report_v.html').as_posix()
    if models[0].model_type == 'soil_model':
        list_file = html_dir_path.joinpath('list_report_s.html').as_posix()

    create_model_list_report_html(models, list_file, html_dir_path)


def create_single_report(yaml_file_name, target_dir):
    target_dir_path = Path(target_dir)
    
    model = Model.from_file(yaml_file_name)
    dir_name = model.bibtex_entry.key
    if model.modelID: dir_name += "-" + model.modelID

    sub_dir = target_dir_path.joinpath(dir_name).as_posix()
    rel = report_from_model(model) 
    rel.create_pandoc_dir(sub_dir)


def parse_args():
    parser = argparse.ArgumentParser(description="Create model database websites.")
    parser.add_argument('-sd', action="store_true",help="create modeldir website from <srcdir> to optional -t <target_dir>")
    parser.add_argument('-s', action="store_true",help="create soil model website to optional -t <target_dir> , default=SoilModels")
    parser.add_argument('-v', action="store_true",help="create vegetation model website to optional -t <target_dir>, default=VegetationModels")
    parser.add_argument('-f', nargs='+', default=None, help="create particular model report/reports to <target_dir> given by the -t option\n Example: generate_website -f Henin1945Annalesagronomiques -t SoilModels/html")

    parser.add_argument('-t', default=None, help="where to generate the html files. \nExample: generate_website -f Henin1945Annalesagronomiques.yaml -t SoilModels/html")

    return parser.parse_args()

def generate_website():
    com = parse_args()
    
    if com.f:
        generate_model_run_report(com)
        
    generate_model_run_reports(com)



    

######################################################################################

#fixme: improve to also use optional input directories?
if __name__ == '__main__':
    print("""
    There is a commandline tool to use directly now. Just run: 
   
    $generate_website 
   
    from anywhere now.""")
    parse_args()

#lachs
#brot
#brotbelag
#bastikaese
