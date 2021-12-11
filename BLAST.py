import numpy as np
import pandas as pd
import time
import re

# Read .fasta file into a dictionary object, containing the chromosome index and the correspond nucleotide sequence.
def FaToDict(filename):
    """
    :param filename: the repository of the .fasta file
    :return: a dictionary which values are the nucleotide sequences
    """
    f = open(filename, 'r')
    dic = {}
    for line in f:
        if line.startswith('>'):
            index = line.replace('>', '').split()[0]
            dic[index] = ''
        else:
            dic[index] += line.replace('\n', '').strip()
    f.close()
    return dic

#Generate reverse and complementary seq
def Rev_Comlementary(DNA):
    """
    Generate the reverse and complementary seq: (-) strand
    :para DNA: query seq or ref genome seq
    :return: the complementary string from 5' to 3'
    """
    com = {'A': 'T', 'a':'T',
           'T': 'A', 't':'A',
           'C': 'G', 'c':'G',
           'G': 'C', 'g':'C'}
    dna = []
    for n in DNA:
        dna.append(com[n])
    return dna

#transform base pair to number to increase the speed
def SymToNum(seq):
    """
    Transform nucleotide into number
    :para word: nucleotide seq
    :return: number list of input seq
    """
    trans = {'a':0,'A':0,'c':1,'C':1,'g':2,'G':2,'t':3,'T':3}
    num = []
    for n in seq:
        num.append(trans[n])
    return num

#score the single pair of nucleotides
def Score(n1,n2):
    """
    Score of two input base pair
    :para n1, n2: base pair from two seq
    :return: alignment score of two nucleotides
    """
    score = 0
    #Order is ACGT
    grade = np.matrix([[4,-7,-5,-7],
                       [-7,4,-7,-5],
                       [-5,-7,4,-7],
                       [-7,-5,-7,4]])
    #align:4, AG&CT-5, other mismatch-7, gap-5
    score = grade[SymToNum(n1),SymToNum(n2)]
    return score

#score two sequence with same length
def ScoreSeq(seq1, seq2):#score seeds
    """
    Score of two input sequence with the same length
    :para seq1,seq2: two sequence of same length
    :return: alignment score of two sequence
    """
    score = 0
    # Order is ACGT
    grade = np.matrix([[4, -7, -5, -7],
                       [-7, 4, -7, -5],
                       [-5, -7, 4, -7],
                       [-7, -5, -7, 4]])
    # align:4, AG&CT-5, other mismatch-7, gap-5
    seq1 = SymToNum(seq1)
    seq2 = SymToNum(seq2)
    for i in range(len(seq1)):
        score = grade[seq1[i], seq2[i]]
    return score

#Simply score two nucleotides using hamming distance
#After matched and merged seeds and before the SW algorithm extending
def hammingScore(q,r):
    """
    :para q,r: base pair from query seq and ref seq
    :return: the hamming distance score
    """
    bothscore = 0
    if q == r:
        bothscore = 2
    else:
        bothscore = -1
    return bothscore

#Smith-Waterman Alignment in extending

#Generate seeds from query seq and store in hash table
def Seed(query):
    """
    Using sliding window to generate seeds from query seq
    :para query: input virus seq
    :retrun: a hash table stores 11-mer seeds (value in list format)
    """
    seed = dict()
    ends = len(query) - 11 + 1
    query = query.upper()
    for i in range(ends):
        q = query[i:i+11]
        if q in seed:  # python3写法
            seed[q].append(i)
        else:
            seed[q] = [i]
    return seed

#Ref genome also need to generate 11-mer seed for 'seeding' step
def genomeSeed(DNA):
    pass

#Transform seq into 4进制数字和
#one optimization to increase the matched speed when comparing the seeds from query and ref
def SeqToNum(seq,len):
    """
    transfer sequence into a sum of SymToNum in 4-scale
    :return: unique sum of seq in 4-scale
    """
    sum = 0
    seq_num = SymToNum(seq)
    for i,n in enumerate(seq_num):
        sum += n*(4**(len-i))
    return sum

#Display BLAST result into BED format

#Merge the overlap and nearby seed into one seed
def merge_seed(match):
    #match is a dataframe with start index of query and ref and length
    """
    Merge the overlapped seeds (end index > another start index) and nearby seeds (end to end) together
    :para match: Start and end index of query and ref genome and length of matched seeds (DataFrame)
    :return: merge_seeds with start and end index of query and ref genome and their length (DataFrame)
    """
    match = match.explode('q') #把query中有重复的分成单独一行
    match = match.reset_index(drop=True)  #reset the row index
    match = match.explode('r')#把ref中有重复的分成单独一行
    #sorted by query index
    match.sort_values('q', axis=0, ascending=True, inplace=True, kind='quicksort', na_position='last')
    match = match.reset_index(drop=True)  #reset the row index
    flag = True #True refers to this seed can be deleted
    for i in range(len(match) - 1):#前面的seed
        j = i + 1
        while j < len(match):
            #在query和ref上距离相等且距离<=seed长度
            if match['q'][j]-match['q'][i] == match['r'][j]-match['r'][i] & (match['q'][j]-match['q'][i]) <= match['l'][i]:
                match['l'][i] = match['q'][j] + match['l'][j] - match['q'][i]
                match.drop(j,inplace = True)
                match = match.reset_index(drop=True)  # reset the row index
            else: j += 1
    return match

#Core BLAST function
#further can add seed thershold and extend thershold
def BLAST(query, ref):
    """
    Core BLAST function, start from query seq and ref genome
    :para query: query seq that already read-in in the main function
    :para ref: ref genome seq that already read-in in the main function
    :return:不确定
    """
    #Generate seeds
    query_seed = {}
    ref_seed = {}
    #matched seeds put in the dataframe
    match_seed = pd.DataFrame(columns=['q','r','l'])
    query_seed = Seed(query)
    ref_seed = Seed(ref)
    #further improvement:define seed selection thershold
    #further improvement: transfer seed seq to sum of 4-scale number

    #compare seeds from query dict and ref genome dict
    for i in query_seed:#for every seed in query dict
        if i in ref_seed:#python3写法
            match_seed = match_seed.append({'q':query_seed[i], 'r':ref_seed[i], 'l': 11},
                              ignore_index = True)#可存list
            #把matched的seed在query和ref genome中对应的index存入一个DF
    #Merge the overlapped and nearby seeds
    merge_seeds = merge_seed(match_seed)#for further extend
    #把生成的seed matrix删掉以释放内存，只留下merge_seed（Dataframe）就可以
    del ref_seed,query_seed
    #First extend using simple hamming distance
    #规定比对的边界（在ref上面长度应略大于query长度（可能ref会有gap））
    for row in range(len(merge_seeds)):#for every merged seed in dataframe（每一行是一个seed）
        ii = 0 #距离seed开头结尾的距离
        sumscore = 2 * merge_seeds['l'][row]#Initial score
        q_start = merge_seeds['q'][row]#start index in query seq
        r_start = merge_seeds['r'][row]#start index in ref seq
        l = merge_seeds['l'][row]#length of the seed
        while sumscore > 0:
            if ii == q_start: break #extend to the first index of query
            if ii == r_start: break #extend to the first index of ref
            sumscore = sumscore + hammingScore(query[q_start-ii],ref[r_start-ii]) \
                       + hammingScore(query[q_start+l+ii],ref[r_start+l+ii])
            ii += 1
            if ii > len(query) - q_start - l: break #此时query已经到了最后，但ref可以更长，此时sumscore就为ref往后延伸的长度
        merge_seeds['q'][row] = q_start - ii
        #SW algorithm
        #matched seed 之前的矩阵

        #matched seed 之后的矩阵

        '''
        #使用打分矩阵计算初步延伸距离
        ii = 0 #extend distance
        sumscore = 2 * merge_seeds['l'][row]#Initial score
        q_start = merge_seeds['q'][row]#start index in query seq
        r_start = merge_seeds['r'][row]#start index in ref seq
        l = merge_seeds['l'][row]#length of the seed
        while sumscore > 0:
        '''




#Main code
#interact with users
print("Please input your query file with the pathway (in .fasta format):")
query_file = input()
print("Please input your reference genome file with the pathway (in .fasta format):")
ref_file = input()
if format is not the .fasta:
    print("Please input the file in .fasta format, please.")

#record the time
starts = time.clock()
query_seq = FaToDict(query_file)
#把一个chr分成很多段，一段一段的进行seed&extend
ref = FaToDict(ref_file)

end = time.clock()
print ("Using time: %fs" % (end-starts))
print('--------------------------------------')
