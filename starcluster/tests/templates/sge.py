#!/usr/bin/env python
qhost_xml = """<?xml version='1.0'?>
<qhost xmlns:xsd="http://gridengine.sunsource.net/source/browse/*checkout*/gridengine/source/dist/util/resources/schemas/qhost/qhost.xsd?revision=1.2">
 <host name='global'>
   <hostvalue name='arch_string'>-</hostvalue>
   <hostvalue name='num_proc'>-</hostvalue>
   <hostvalue name='load_avg'>-</hostvalue>
   <hostvalue name='mem_total'>-</hostvalue>
   <hostvalue name='mem_used'>-</hostvalue>
   <hostvalue name='swap_total'>-</hostvalue>
   <hostvalue name='swap_used'>-</hostvalue>
 </host>
 <host name='ip-10-196-142-180.ec2.internal'>
   <hostvalue name='arch_string'>lx24-x86</hostvalue>
   <hostvalue name='num_proc'>1</hostvalue>
   <hostvalue name='load_avg'>0.03</hostvalue>
   <hostvalue name='mem_total'>1.7G</hostvalue>
   <hostvalue name='mem_used'>75.4M</hostvalue>
   <hostvalue name='swap_total'>896.0M</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='ip-10-196-214-162.ec2.internal'>
   <hostvalue name='arch_string'>lx24-x86</hostvalue>
   <hostvalue name='num_proc'>1</hostvalue>
   <hostvalue name='load_avg'>0.21</hostvalue>
   <hostvalue name='mem_total'>1.7G</hostvalue>
   <hostvalue name='mem_used'>88.9M</hostvalue>
   <hostvalue name='swap_total'>896.0M</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
 <host name='ip-10-196-215-50.ec2.internal'>
   <hostvalue name='arch_string'>lx24-x86</hostvalue>
   <hostvalue name='num_proc'>1</hostvalue>
   <hostvalue name='load_avg'>0.06</hostvalue>
   <hostvalue name='mem_total'>1.7G</hostvalue>
   <hostvalue name='mem_used'>75.9M</hostvalue>
   <hostvalue name='swap_total'>896.0M</hostvalue>
   <hostvalue name='swap_used'>0.0</hostvalue>
 </host>
</qhost>"""

qstat_xml = """<?xml version='1.0'?>
<job_info  xmlns:xsd="http://gridengine.sunsource.net/source/browse/*checkout*/gridengine/source/dist/util/resources/schemas/qstat/qstat.xsd?revision=1.11">
  <queue_info>
    <job_list state="running">
      <JB_job_number>1</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>r</state>
      <JAT_start_time>2010-06-18T23:39:24</JAT_start_time>
      <queue_name>all.q@ip-10-196-142-180.ec2.internal</queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="running">
      <JB_job_number>2</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>r</state>
      <JAT_start_time>2010-06-18T23:39:24</JAT_start_time>
      <queue_name>all.q@ip-10-196-215-50.ec2.internal</queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="running">
      <JB_job_number>3</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>r</state>
      <JAT_start_time>2010-06-18T23:39:24</JAT_start_time>
      <queue_name>all.q@ip-10-196-214-162.ec2.internal</queue_name>
      <slots>1</slots>
    </job_list>
  </queue_info>
  <job_info>
    <job_list state="pending">
      <JB_job_number>4</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:14</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>5</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:14</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>6</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:14</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>7</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:15</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>8</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:15</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>9</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:16</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>10</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:16</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>11</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:17</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>12</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>13</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:35</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>14</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:36</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>15</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:36</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>16</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:37</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>17</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:37</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>18</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:38</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>19</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:38</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>20</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:38</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>21</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:39</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>22</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:39</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
    <job_list state="pending">
      <JB_job_number>23</JB_job_number>
      <JAT_prio>0.55500</JAT_prio>
      <JB_name>sleep</JB_name>
      <JB_owner>root</JB_owner>
      <state>qw</state>
      <JB_submission_time>2010-06-18T23:39:40</JB_submission_time>
      <queue_name></queue_name>
      <slots>1</slots>
    </job_list>
  </job_info>
</job_info>"""

