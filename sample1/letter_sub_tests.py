import letter_sub as a


def test_basic():

    gold_input = 'acadian asset management'
    gold_encrypted = 'agahjac aeebf dacaibdbcf'
    decoder_string = 'a,6,a\ne,3,b\nn,3,c\nm,2,d\ns,2,e\nt,2,f\nc,1,g\nd,1,h\ng,1,i\ni,1,j'
    run(gold_input, gold_encrypted, decoder_string)


def test_nonalpha():
    gold_input = "erin owns it! 1/26/23"
    gold_encrypted = "ceab dhbf ag! 1/26/23"
    decoder_string = "i,2,a\nn,2,b\ne,1,c\no,1,d\nr,1,e\ns,1,f\nt,1,g\nw,1,h"
    run(gold_input, gold_encrypted, decoder_string)


def run(gold_input, gold_encrypted, decoder_string):

    parsed_decoder = a.parse_decoder(decoder_string)
    decoder = a.create_decoder(gold_input)
    assert(decoder == parsed_decoder)

    test_encrypted = a.encrypt(gold_input, decoder)
    assert(test_encrypted == gold_encrypted)

    test_decoder = a.decoder_to_string(decoder)
    assert(test_decoder == decoder_string)
    
    test_decrypted = a.decrypt(test_encrypted, decoder)
    assert(test_decrypted == gold_input)

