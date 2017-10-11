import argparse
from iic.models import PageInputGroup, PageInput
from administration.models import Gateway

parser = argparse.ArgumentParser()

# parser.add_argument("-m", help="model")
# parser.add_argument("-i", help="model Id")
# parser.add_argument("-f", help="favour")


def run(pk):
    # args = parser.parse_args()
    # if args.i:
    #     id = args.i
    # else:
    #    print 'ID not provided'
    #    return

    if not pk:return

    gateways = Gateway.objects.all()

    page_input_group = PageInputGroup.objects.get(id=pk)
    page_inputs = PageInput.objects.filter(page_input_group=page_input_group).order_by('item_level')
    for index, page_input in enumerate(page_inputs):
        # page_input.item_level = index
        # page_input.save()
        
        if page_input.pk == 963 or page_input.pk == 964 or page_input.pk == 961:
            page_input.gateway.add(*gateways)
        else:
            page_input.gateway.add(*gateways.exclude(name='WahiLoan'))
