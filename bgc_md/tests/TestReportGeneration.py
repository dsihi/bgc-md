#!/usr/bin/env python3
# vim:set ff=unix expandtab ts=4 sw=4:
import unittest
import sys
from concurrencytest import ConcurrentTestSuite, fork_for_tests
from pathlib import Path
from shutil import copytree
from bgc_md.Model import Model
from testinfrastructure.InDirTest import InDirTest
from bgc_md.reports import produce_model_report_markdown, produce_model_report_markdown_directory, create_html_from_pandoc_md, create_html_from_pandoc_md_directory,generate_website
from bgc_md.yaml_creator_mod import example_yaml_string_list2
from bgc_md.helpers import remove_indentation
from bgc_md.reports import defaults
import bgc_md.gv as gv

class TestReportGeneration(InDirTest):

   # def setUp(self):
   #     self.yaml_str_list = example_yaml_string_list2() 
   #     self.yaml_file_names=[]
   #     for index, yaml_str in enumerate(self.yaml_str_list):
   #         yaml_input_file_name = "testfile" + str(index) + ".yaml"
   #         with open(yaml_input_file_name, "w") as f:
   #             f.write(yaml_str)

    #@unittest.skip("takes too long")
    def test_commandline_tools(self):
        d=defaults() 
        vp=d['paths']['veg']
        here=Path('.')
        targetPath=here.joinpath('veg')
        targetPath.mkdir()
        for rec in  vp.iterdir():
            print(rec)

        #dir_names=[Model.from_str(ys) for ys in self.yaml_str_list]
        # fixme
        #to be continued

    @unittest.skip("function under test calls report_from_yaml_str which is commented out")
    def test_report_html_presence(self):
    # fixme
    # to be deprecated
        for index, yaml_str in enumerate(self.yaml_str_list):
            trunk = "testfile" + str(index)
            yaml_file_name = trunk + ".yaml"
            markdown_file_name = trunk + ".md"
            html_file_name = trunk + ".html"
            csl_file_name = gv.resources_path.joinpath('apa.csl').as_posix()
            css_file_name = gv.resources_path.joinpath('buttondown.css').as_posix()

            # yaml -> md, bibtex -> html
            produce_model_report_markdown(yaml_file_name, markdown_file_name)
            create_html_from_pandoc_md(markdown_file_name, html_file_name,
                                        csl_file_name=csl_file_name, css_file_name=css_file_name, slide_show=False)
            #check if the result has been produced where we expected 
            self.assertTrue(Path(html_file_name).exists())

            # yaml -> md, bibtex -> html (slide show)
            html_file_name = trunk + "_ss.html"
            produce_model_report_markdown(yaml_file_name, markdown_file_name)
            create_html_from_pandoc_md(markdown_file_name, html_file_name,
                                        csl_file_name=csl_file_name, css_file_name=css_file_name, slide_show=True)
            #check if the result has been produced where we expected 
            self.assertTrue(Path(html_file_name).exists())

    @unittest.skip("function under test calls report_from_yaml_str which is commented out")
    def test_report_html_presence_directory(self):
    # fixme
    # to be deprecated
        csl_file_name = gv.resources_path.joinpath('apa.csl').as_posix()
        css_file_name = gv.resources_path.joinpath('buttondown.css').as_posix()
        produce_model_report_markdown_directory("", "md")
        create_html_from_pandoc_md_directory("md", "html", csl_file_name=csl_file_name, css_file_name=css_file_name)
        

####################################################################################################
if __name__ == '__main__':
    suite=unittest.defaultTestLoader.discover(".",pattern=__file__)
    # Run same tests across 16 processes
    concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(16))
    runner = unittest.TextTestRunner()
    res=runner.run(concurrent_suite)
    # to let the buildbot fail we set the exit value !=0 if either a failure or error occurs
    if (len(res.errors)+len(res.failures))>0:
        sys.exit(1)
