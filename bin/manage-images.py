#!/usr/bin/env python

from optparse import OptionParser
from molsim.ec2utils import list_registered_images, remove_image, list_image_files
from molsim.s3utils import list_buckets, show_bucket_files 

def main():
    usage = "usage: %prog [options] "
    parser = OptionParser(usage)

    parser.add_option("-l","--list-images", dest="list_images", action="store_true", default=False, help="list all registered ec2 images")
    parser.add_option("-f","--show-image-files", dest="show_image", default=None, help="show all files on s3 for the an ec2 image")
    parser.add_option("-b","--list-buckets", dest="list_buckets", action="store_true", default=False, help="list all s3 buckets")
    parser.add_option("-s","--show-bucket-files", dest="show_bucket", default=None, help="show all files in bucket")
    parser.add_option("-r","--remove-image", dest="remove_image", default=None, help="deregister an ec2 image and remove it from s3")

    (options,args) = parser.parse_args() 

    if options.list_images:
        list_registered_images()
    elif options.list_buckets:
        list_buckets()
    elif options.show_bucket:
        show_bucket_files(options.show_bucket)
    elif options.remove_image:
        remove_image(options.remove_image, pretend=True)
    elif options.show_image:
        list_image_files(options.show_image)
    else:
        parser.print_help()
    
if __name__ == "__main__":
    main()
