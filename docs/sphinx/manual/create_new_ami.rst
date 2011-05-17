Creating a New AMI From the StarCluster AMI
===========================================
The StarCluster base AMIs are meant to be fairly minimal in terms of the software installed. If you'd like to have an
additional set of software installed on the AMI you can use StarCluster to create a new version of the StarCluster AMIs.

To do this, use either `ElasticFox <http://developer.amazonwebservices.com/connect/entry.jspa?externalID=609>`_ or the 
`Amazon Web Services <https://console.aws.amazon.com/ec2/home>`_ console to start a single instance of either the 32bit 
or 64bit StarCluster AMI. Once this instance has come up, login and customize the software installed on the AMI using 
either *apt-get* or by manually installing the software from source. 

Once you've finished customizing the software installed on the instance, you can then run StarCluster's **createimage**
command to create a new AMI.

.. code-block:: none

        $ starcluster createimage i-9999999 my-new-image mybucket

In this command, i-99999999 is the instance id of the instance you wish to create a new image from. *my-new-image* is the 
name of the image (or AMI prefix) and *mybucket* is the bucket in S3 to store your new AMI in.

After this command completes it should print out the new AMI id that you can now use in the node_image_id/master_image_id
settings in your *cluster templates*.
